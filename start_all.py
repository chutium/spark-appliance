#!/usr/bin/env python3

import os
import time
import logging
import requests
import subprocess

logging.basicConfig(level=getattr(logging, 'INFO', None))

spark_dir = os.getenv('SPARK_DIR')
master_string = os.getenv('MASTER_STRING')


def get_private_ip():
    url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
    try:
        response = requests.get(url)
        json = response.json()
        return json['privateIp']
    except requests.exceptions.ConnectionError:
        return "127.0.0.1"

private_ip = get_private_ip()

if os.getenv('ZOOKEEPER_STACK_NAME').lower() != "":
    logging.info("TODO: set SPARK_DAEMON_JAVA_OPTS")

if os.getenv('HIVE_SITE_XML').lower() != "":
    logging.info("TODO: get hive-site from s3 or http")

log_watchers = {}

if os.getenv('START_MASTER').lower() == 'true':
    os.environ['SPARK_MASTER_IP'] = private_ip
    master_log = subprocess.check_output([spark_dir + "/sbin/start-master.sh"], universal_newlines=True)
    log_watchers['Master'] = subprocess.Popen(["tail", "-f", master_log.rsplit(None, 1)[-1]])

if os.getenv('ZOOKEEPER_STACK_NAME').lower() != "":
    logging.info("TODO: generate master_string from ELB")
    logging.info("TODO: get master_ip from zookeeper")
else:
    master_ip = private_ip
    if master_string == "":
        master_string = "spark://" + master_ip + ":7077"

if os.getenv('START_WORKER').lower() == 'true':
    if os.getenv('START_MASTER').lower() != 'true':
        os.environ['SPARK_WORKER_PORT'] = "7077"
    worker_log = subprocess.check_output([spark_dir + "/sbin/start-slave.sh", master_string], universal_newlines=True)
    log_watchers['Worker'] = subprocess.Popen(["tail", "-f", worker_log.rsplit(None, 1)[-1]])

if os.getenv('START_THRIFTSERVER').lower() == 'true':
    time.sleep(30)
    thriftserver_log = subprocess.check_output([spark_dir + "/sbin/start-thriftserver.sh",
                                                "--master", master_string,
                                                "--hiveconf", "hive.server2.thrift.port=10000",
                                                "--hiveconf", "hive.server2.thrift.bind.host=" + master_ip],
                                               universal_newlines=True)
    log_watchers['ThriftServer'] = subprocess.Popen(["tail", "-f", thriftserver_log.rsplit(None, 1)[-1]])

while True:
    time.sleep(60)
    for name, watcher in iter(log_watchers.items()):
        status = watcher.poll()
        if status is None:
            logging.info(name + " is running...")
            continue
        elif status == 0:
            logging.info(name + " stopped.")
            continue
        else:
            logging.info(name + " failed.")
            logging.info("Log watcher failed with status: ", str(status))
