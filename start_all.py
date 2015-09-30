#!/usr/bin/env python3

import os
import time
import boto3
import logging
import requests
import subprocess
from kazoo.client import KazooClient

logging.basicConfig(level=getattr(logging, 'INFO', None))

spark_dir = os.getenv('SPARK_DIR')
masterUri = os.getenv('MASTER_URI')
master_ip = ""

url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
try:
    response = requests.get(url)
    json = response.json()
    instanceId = json['instanceId']
    private_ip = json['privateIp']
    region = json['region']
except requests.exceptions.ConnectionError:
    instanceId = "127.0.0.1"
    private_ip = "127.0.0.1"
    region = None

if os.getenv('ZK_CONN_STR').lower() != "":
    os.environ['SPARK_DAEMON_JAVA_OPTS'] = "-Dspark.deploy.recoveryMode=ZOOKEEPER -Dspark.deploy.zookeeper.url=" + os.getenv('ZK_CONN_STR')
    logging.info("HA mode enabled...")

if os.getenv('HIVE_SITE_XML').lower() != "":
    logging.info("TODO: get hive-site from s3 or http")

log_watchers = {}

if os.getenv('START_MASTER').lower() == 'true':
    os.environ['SPARK_MASTER_IP'] = private_ip
    master_log = subprocess.check_output([spark_dir + "/sbin/start-master.sh"], universal_newlines=True)
    log_watchers['Master'] = subprocess.Popen(["tail", "-f", master_log.rsplit(None, 1)[-1]])


def get_master_uri(instanceId, private_ip, region):
    master_ips = []

    if region is not None:
        elb = boto3.client('elb', region_name=region)
        ec2 = boto3.client('ec2', region_name=region)

        response = elb.describe_load_balancers()
        found = False
        for loadbalancer in response['LoadBalancerDescriptions']:
            for instance in loadbalancer['Instances']:
                if instance['InstanceId'] == instanceId:
                    lb_name = loadbalancer['LoadBalancerName']
                    found = True
                    break
            if found:
                break

        cluster_size = int(os.getenv('CLUSTER_SIZE'))
        master_ips = []
        while len(master_ips) != cluster_size:
            time.sleep(10)
            response = elb.describe_instance_health(LoadBalancerName=lb_name)
            master_ips = []
            for instance in response['InstanceStates']:
                if instance['State'] == 'InService':
                    master_ips.append(ec2.describe_instances(
                        InstanceIds=[instance['InstanceId']])['Reservations'][0]['Instances'][0]['PrivateIpAddress'])
    else:
        master_ips = [private_ip]

    master_str = ''
    for ip in master_ips:
        master_str += ip + ':7077,'

    logging.info("HA mode enabled, using spark master URI: " + "spark://" + master_str[:-1])
    return "spark://" + master_str[:-1]


def get_active_master_ip(zk_conn_str):
    zk = KazooClient(hosts=zk_conn_str)
    zk.start()
    try:
        master_ip = zk.get("/spark/leader_election/current_master")[0].decode('utf-8')
        logging.info("HA mode enabled, active spark master: " + master_ip)
        zk.stop()
    except:
        master_ip = ""
        logging.warning("ERROR: HA mode enabled, but no active spark master founded!")
        zk.stop()
    return master_ip

if os.getenv('ZK_CONN_STR').lower() != "":
    if masterUri == "":
        masterUri = get_master_uri(instanceId, private_ip, region)
    master_ip = get_active_master_ip(os.getenv('ZK_CONN_STR'))

if master_ip == "":
    master_ip = private_ip

if masterUri == "":
    masterUri = "spark://" + master_ip + ":7077"

if os.getenv('START_WORKER').lower() == 'true':
    if os.getenv('START_MASTER').lower() != 'true':
        os.environ['SPARK_WORKER_PORT'] = "7077"
        logging.info("Spark master daemon not started, worker daemon will bind to port 7077.")
    else:
        logging.info("Spark master daemon running on port 7077, worker bind to random port.")

    worker_log = subprocess.check_output([spark_dir + "/sbin/start-slave.sh", masterUri], universal_newlines=True)
    log_watchers['Worker'] = subprocess.Popen(["tail", "-f", worker_log.rsplit(None, 1)[-1]])

if os.getenv('START_THRIFTSERVER').lower() == 'true':
    if master_ip == private_ip:
        time.sleep(30)
        logging.info("Start thrift server only on current active spark master node.")
        thriftserver_log = subprocess.check_output([spark_dir + "/sbin/start-thriftserver.sh",
                                                    "--master", masterUri,
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
