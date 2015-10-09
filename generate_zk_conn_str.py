#!/usr/bin/env python3

import boto3


def run(stack_name, region=None):
    private_ips = []

    if region is not None:
        elb = boto3.client('elb', region_name=region)
        ec2 = boto3.client('ec2', region_name=region)

        response = elb.describe_instance_health(LoadBalancerName=stack_name)

        for instance in response['InstanceStates']:
            if instance['State'] == 'InService':
                private_ips.append(ec2.describe_instances(
                    InstanceIds=[instance['InstanceId']])['Reservations'][0]['Instances'][0]['PrivateIpAddress'])

    else:
        private_ips = [stack_name]

    zk_conn_str = ''
    for ip in private_ips:
        zk_conn_str += ip + ':2181,'

    return zk_conn_str[:-1]
