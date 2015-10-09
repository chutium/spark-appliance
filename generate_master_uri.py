import boto3
import time


def get_master_ips(elb, ec2, stack_name):
    master_ips = []
    response = elb.describe_instance_health(LoadBalancerName=stack_name)
    for instance in response['InstanceStates']:
        if instance['State'] == 'InService':
            master_ips.append(ec2.describe_instances(
                InstanceIds=[instance['InstanceId']])['Reservations'][0]['Instances'][0]['PrivateIpAddress'])
    return master_ips


def run(master_stack_name, instanceId, private_ip, region, cluster_size):
    master_ips = []

    if region is not None:
        elb = boto3.client('elb', region_name=region)
        ec2 = boto3.client('ec2', region_name=region)

        stack_name = master_stack_name

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
            if stack_name == "":
                return ""

            master_ips = get_master_ips(elb, ec2, stack_name)
            while len(master_ips) != cluster_size:
                time.sleep(10)
                master_ips = get_master_ips(elb, ec2, stack_name)
        else:
            master_ips = get_master_ips(elb, ec2, stack_name)
    else:
        master_ips = [private_ip]

    master_ips.sort()
    master_str = ''
    for ip in master_ips:
        master_str += ip + ':7077,'

    return "spark://" + master_str[:-1]
