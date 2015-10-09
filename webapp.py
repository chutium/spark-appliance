#!/usr/bin/env python3
import os
import sys
import logging
import connexion
import generate_master_uri
import get_alive_master_ip

master_stack_name = sys.argv[1]
if master_stack_name == "NONE":
    master_stack_name = ""
instanceId = sys.argv[2]
private_ip = sys.argv[3]
region = sys.argv[4]
if region == "NONE":
    region = None
cluster_size = int(sys.argv[5])
zk_conn_str = sys.argv[6]
if zk_conn_str == "NONE":
    zk_conn_str = ""


def get_master_uri():
    if zk_conn_str != "":
        return generate_master_uri.run(master_stack_name, instanceId, private_ip, region, cluster_size)
    else:
        return "spark://" + get_master_ip() + ":7077"


def get_master_ip():
    if zk_conn_str != "":
        return get_alive_master_ip.run(zk_conn_str)
    else:
        return private_ip

logging.basicConfig(level=getattr(logging, 'INFO', None))

api_args = {'auth_url': os.environ.get('AUTH_URL'), 'tokeninfo_url': os.environ.get('TOKENINFO_URL')}
webapp = connexion.App(__name__, port=8080, debug=True, server='gevent')
webapp.add_api('swagger.yaml', arguments=api_args)
application = webapp.app

if __name__ == '__main__':
    webapp.run()
