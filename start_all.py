#!/usr/bin/env python3

import os
import boto3
import logging
import subprocess
import utils
from time import sleep

logging.basicConfig(level=getattr(logging, 'INFO', None))

spark_dir = utils.get_os_env('SPARK_DIR')

utils.set_ec2_identities()

zk_conn_str = ""
if utils.get_os_env('ZOOKEEPER_STACK_NAME') != "":
    zk_conn_str = utils.generate_zk_conn_str()
    os.environ['SPARK_DAEMON_JAVA_OPTS'] = "-Dspark.deploy.recoveryMode=ZOOKEEPER " \
                                           "-Dspark.deploy.zookeeper.url=" + zk_conn_str
    logging.info("HA mode enabled with ZooKeeper connection string " + zk_conn_str)

os.environ['ZOOKEEPER_CONN_STR'] = zk_conn_str

if utils.get_os_env('HIVE_SITE_XML') != "":
    hive_site_xml = utils.get_os_env('HIVE_SITE_XML')
    path = hive_site_xml[5:]
    bucket = path[:path.find('/')]
    file_key = path[path.find('/')+1:]
    s3 = boto3.resource('s3')
    try:
        s3.meta.client.download_file(bucket, file_key, spark_dir + '/conf/hive-site.xml')
        logging.info("Got hive-site.xml from " + hive_site_xml)
    except:
        logging.error("ERROR: Failed to get hive-site.xml from " + hive_site_xml)

log_watchers = {}

if utils.get_os_env('START_MASTER').lower() == 'true':
    os.environ['SPARK_MASTER_IP'] = utils.get_private_ip()
    master_log = subprocess.check_output([spark_dir + "/sbin/start-master.sh"], universal_newlines=True)
    log_watchers['Master'] = subprocess.Popen(["tail", "-f", master_log.rsplit(None, 1)[-1]])

master_stack_name = utils.get_os_env('MASTER_STACK_NAME')
master_uri = ""
master_ip = ""

if zk_conn_str != "":
    master_uri = utils.generate_master_uri()
    logging.info("HA mode enabled, using spark master URI: " + master_uri)
    master_ip = utils.get_alive_master_ip()
    logging.info("HA mode enabled, current alive spark master: " + master_ip)
elif master_stack_name != "":
    master_uri = utils.generate_master_uri()
    logging.info("Cluster mode enabled, using spark master URI: " + master_uri)
    master_ip = utils.get_alive_master_ip()
    logging.info("Cluster mode enabled, current alive spark master: " + master_ip)

if master_ip == "":
    master_ip = utils.get_private_ip()

if master_uri == "":
    master_uri = "spark://" + master_ip + ":7077"

start_worker = utils.get_os_env('START_WORKER').lower()


def create_worker_process(masterUri):
    global start_worker
    global log_watchers
    if start_worker == 'true':
        if utils.get_os_env('START_MASTER').lower() != 'true':
            os.environ['SPARK_WORKER_PORT'] = "7077"
            logging.info("Spark master daemon not started, worker daemon will bind to port 7077.")
        else:
            logging.info("Spark master daemon running on port 7077, worker bind to random port.")

        worker_log = subprocess.check_output([spark_dir + "/sbin/start-slave.sh", masterUri], universal_newlines=True)
        log_watchers['Worker'] = subprocess.Popen(["tail", "-f", worker_log.rsplit(None, 1)[-1]])

create_worker_process(master_uri)

if utils.get_os_env('START_THRIFTSERVER').lower() == 'true':
    if master_ip == utils.get_private_ip():
        sleep(30)
        logging.info("Start thrift server only on current active spark master node.")
        thriftserver_log = subprocess.check_output([spark_dir + "/sbin/start-thriftserver.sh",
                                                    "--master", master_uri,
                                                    "--hiveconf", "hive.server2.thrift.port=10000",
                                                    "--hiveconf", "hive.server2.thrift.bind.host=0.0.0.0"],
                                                   universal_newlines=True)
        log_watchers['ThriftServer'] = subprocess.Popen(["tail", "-f", thriftserver_log.rsplit(None, 1)[-1]])

if utils.get_os_env('START_WEBAPP').lower() == 'true':
    logging.info("Daemon started, starting webapp now...")
    log_watchers['WebApp'] = subprocess.Popen(["uwsgi", "--http", ":8000", "-w", "webapp"])

master_size = len(master_uri.split(','))
checker = 1

while True:
    sleep(60)
    if checker % 10 == 0 and start_worker == 'true':
        if utils.get_os_env('ZOOKEEPER_STACK_NAME') != "" or utils.get_os_env('MASTER_STACK_NAME') != "":
            logging.info("Checking if MasterURI changed...")
            old_master_uri = master_uri
            master_uri = utils.generate_master_uri()
            if master_uri != old_master_uri:
                if len(master_uri.split(',')) == master_size:
                    logging.info("MasterURI changed, restarting spark worker...")
                    stop_worker = subprocess.Popen([spark_dir + "/sbin/stop-slave.sh"])
                    stop_worker.wait()
                    sleep(5)
                    create_worker_process(master_uri)
                else:
                    logging.info("MasterURI changed, waiting for new master node coming back...")
    for name, watcher in iter(log_watchers.items()):
        status = watcher.poll()
        if status is None:
            logging.info(name + " is running since " + str(checker) + " minutes ...")
            continue
        elif status == 0:
            logging.info(name + " stopped.")
            continue
        else:
            logging.info(name + " failed.")
            logging.info("Log watcher failed with status: ", str(status))
    checker += 1
