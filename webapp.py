#!/usr/bin/env python3

import logging
import connexion
import utils

utils.set_ec2_identities()
private_ip = utils.get_private_ip()


def get_master_uri():
    master_uri = utils.generate_master_uri()
    if master_uri != "":
        return master_uri
    else:
        return "spark://" + private_ip + ":7077"


def get_master_ip():
    master_ip = utils.get_alive_master_ip()
    if master_ip != "":
        return master_ip
    else:
        return private_ip


def get_thrift_server_uri():
    thrift_server_uri = utils.generate_thrift_server_uri()
    if thrift_server_uri != "":
        return thrift_server_uri
    else:
        return "Not found: Thrift server not running!", 404


logging.basicConfig(level=getattr(logging, 'INFO', None))

api_args = {'auth_url': utils.get_os_env('AUTH_URL'), 'tokeninfo_url': utils.get_os_env('TOKENINFO_URL')}
webapp = connexion.App(__name__, port=8080, debug=True, server='gevent')
webapp.add_api('swagger.yaml', arguments=api_args)
application = webapp.app

if __name__ == '__main__':
    webapp.run()
