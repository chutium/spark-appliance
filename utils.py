#!/usr/bin/env python3

import os
import boto3
import requests

instanceId = "127.0.0.1"
private_ip = "127.0.0.1"
region = None


def get_os_env(name):
    os_env = os.getenv(name, "")
    return os_env.strip()


def set_ec2_identities():
    url = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
    try:
        response = requests.get(url, timeout=(3, 27))
        json = response.json()
        global instanceId
        global private_ip
        global region
        instanceId = json['instanceId']
        private_ip = json['privateIp']
        region = json['region']
        return True
    except requests.exceptions.ConnectionError:
        return False


def get_private_ip():
    global private_ip
    return private_ip


def get_region():
    global region
    return region


def get_instance_ips(elb, ec2, stack_name):
    instance_ips = []
    response = elb.describe_instance_health(LoadBalancerName=stack_name)
    for instance in response['InstanceStates']:
        if instance['State'] == 'InService':
            instance_ips.append(ec2.describe_instances(
                InstanceIds=[instance['InstanceId']])['Reservations'][0]['Instances'][0]['PrivateIpAddress'])
    return instance_ips


def generate_zk_conn_str():
    global region
    import re
    stack_name = get_os_env('ZOOKEEPER_STACK_NAME')
    zknode_ips = []

    if re.match(r"^[\w\+-_]+:\d{4,5}", stack_name):  # match 192.168.9.10:1234 or localhost:65535
        return stack_name

    if region is not None:
        elb = boto3.client('elb', region_name=region)
        ec2 = boto3.client('ec2', region_name=region)
        zknode_ips = get_instance_ips(elb, ec2, stack_name)
    else:
        zknode_ips = [stack_name]

    zk_conn_str = ''
    for ip in zknode_ips:
        zk_conn_str += ip + ':2181,'

    return zk_conn_str[:-1]


def generate_master_uri():
    global instanceId
    global private_ip
    global region
    from time import sleep
    stack_name = get_os_env('MASTER_STACK_NAME')
    master_ips = []

    if stack_name.startswith('spark://'):
        return stack_name

    if region is not None:
        elb = boto3.client('elb', region_name=region)
        ec2 = boto3.client('ec2', region_name=region)

        if stack_name == "":
            response = elb.describe_load_balancers()
            found = False
            for loadbalancer in response['LoadBalancerDescriptions']:
                for instance in loadbalancer['Instances']:
                    if instance['InstanceId'] == instanceId:
                        stack_name = loadbalancer['LoadBalancerName']
                        found = True
                        break
                if found:
                    break
            if stack_name == "":  # master node is not in an ELB
                return ""
            else:
                os.environ['MASTER_STACK_NAME'] = stack_name

            master_ips = get_instance_ips(elb, ec2, stack_name)
            cluster_size = int(get_os_env('CLUSTER_SIZE'))
            while len(master_ips) != cluster_size:
                sleep(10)
                master_ips = get_instance_ips(elb, ec2, stack_name)
        else:
            master_ips = get_instance_ips(elb, ec2, stack_name)
    else:
        master_ips = [private_ip]

    master_ips.sort()
    master_str = ''
    for ip in master_ips:
        master_str += ip + ':7077,'

    return "spark://" + master_str[:-1]


def get_alive_master_ip():
    zk_conn_str = get_os_env('ZOOKEEPER_CONN_STR')
    master_stack_name = get_os_env('MASTER_STACK_NAME')
    master_ip = ""
    global region
    if zk_conn_str != "":
        from kazoo.client import KazooClient
        zk = KazooClient(hosts=zk_conn_str)
        zk.start()
        try:
            master_ip = zk.get("/spark/leader_election/current_master")[0].decode('utf-8')
            zk.stop()
        except:
            master_ip = ""
            zk.stop()
        return master_ip
    elif master_stack_name != "" and region is not None:
        try:
            elb = boto3.client('elb', region_name=region)
            ec2 = boto3.client('ec2', region_name=region)
            master_ips = get_instance_ips(elb, ec2, master_stack_name)
            if len(master_ips) != 1:
                return ""  # shouldn't happen without zookeeper
            elif len(master_ips) == 1:
                return master_ips[0]
            else:
                return ""
        except:
            return ""
    else:
        return ""


def try_tcp_conn(ip, port=10000, interval=2, retry=3):
    import socket
    from time import sleep
    timeout_count = 0
    done = False
    while timeout_count < retry and done is False:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((ip, port))
        if result == 0:
            done = True
            return True
        else:
            timeout_count = timeout_count + 1
            sleep(interval)
    return False


def get_thrift_server_ip():
    current_alive_master_ip = get_alive_master_ip()
    master_stack_name = get_os_env('MASTER_STACK_NAME')
    global region
    global private_ip
    if current_alive_master_ip != "" and try_tcp_conn(current_alive_master_ip):
        return current_alive_master_ip
    elif master_stack_name != "" and region is not None:
        elb = boto3.client('elb', region_name=region)
        ec2 = boto3.client('ec2', region_name=region)
        stack_name = get_os_env('MASTER_STACK_NAME')
        master_ips = get_instance_ips(elb, ec2, stack_name)
        for ip in master_ips:
            if try_tcp_conn(ip):
                return ip
        return ""
    elif try_tcp_conn(private_ip):
        return private_ip
    else:
        return ""


def generate_thrift_server_uri():
    thrift_server_ip = get_thrift_server_ip()
    if thrift_server_ip != "":
        return "jdbc:hive2://" + thrift_server_ip + ":10000/"
    else:
        return ""


def get_unique_id():
    import time
    import string
    import random
    chars = string.ascii_uppercase + string.digits
    size = 4
    return str(time.time()) + "-" + ''.join(random.choice(chars) for _ in range(size))
