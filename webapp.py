#!/usr/bin/env python3

import logging
import connexion
from flask import request
import utils

utils.set_ec2_identities()
private_ip = utils.get_private_ip()
job_watchers = {}


def get_dummy():
    return "It works."


def get_twintip():
    return "{}"


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


def get_job_id_from_attached_file():
    try:
        file_stream = request.files['file']
        file_content = file_stream.stream.read()
        unique_id = utils.get_unique_id()
        job_file_id = unique_id + "-" + file_stream.filename
        with open("/tmp/" + job_file_id, "wb") as job_file:
            job_file.write(file_content)
        return job_file_id
    except:
        return ""


def send_query():
    try:
        job_id = get_job_id_from_attached_file()

        hive_vars = request.form.get('hive_vars', "").split()
        arg_hivevar = []
        if len(hive_vars) > 0:
            for hive_var in hive_vars:
                arg_hivevar += ['--hivevar', hive_var]

        hive_confs = request.form.get('hive_confs', "").split()
        arg_hiveconf = []
        if len(hive_confs) > 0:
            for hive_conf in hive_confs:
                arg_hiveconf += ['--hiveconf', hive_conf]

        application_id = utils.get_os_env('APPLICATION_ID')
        application_version = utils.get_os_env('APPLICATION_VERSION')
        hostname = utils.get_os_env('HOSTNAME')
        default_username = application_id + "-" + application_version + "-" + hostname

        username = request.form.get('username', default_username)
        arg_username = ['-n', username]

        password = request.form.get('password', "")
        arg_password = []
        if password != "":
            arg_password = ['-p', password]

        import subprocess
        job_watchers[job_id] = subprocess.Popen(["/opt/beeline/beeline", "-u", get_thrift_server_uri()] +
                                                arg_hivevar + arg_hiveconf + arg_username + arg_password +
                                                ["-f", "/tmp/" + job_id],
                                                universal_newlines=True,
                                                stdout=subprocess.PIPE)
        return job_id
    except:
        return "Failed!", 500


def submit_application():
    try:
        job_id = get_job_id_from_attached_file()
        job_settings = request.form.get('job_settings', "").split()
        job_args = request.form.get('job_args', "").split()
        main_class = request.form.get('main_class', None)
        spark_dir = utils.get_os_env('SPARK_DIR')
        import subprocess
        if main_class is not None:
            job_watchers[job_id] = subprocess.Popen([spark_dir + "/bin/spark-submit",
                                                     "--class", main_class,
                                                     "--master", get_master_uri(),
                                                     "--jars", "/tmp/" + job_id] + job_settings +
                                                    ["/tmp/" + job_id] + job_args,
                                                    universal_newlines=True,
                                                    stdout=subprocess.PIPE)
        else:
            job_watchers[job_id] = subprocess.Popen([spark_dir + "/bin/spark-submit",
                                                     "--master", get_master_uri(),
                                                     "--py-files", "/tmp/" + job_id] + job_settings +
                                                    ["/tmp/" + job_id] + job_args,
                                                    universal_newlines=True,
                                                    stdout=subprocess.PIPE)
        return job_id
    except:
        return "Failed!", 500


def get_job_status(job_id):
    if job_id in job_watchers:
        status = job_watchers[job_id].poll()
        if status is None:
            return {'job_id': job_id, 'status': 'running'}, 200
        elif status == 0:
            return {'job_id': job_id, 'status': 'finished'}, 201
        else:
            return {'job_id': job_id, 'status': 'failed'}, 500
    else:
        return {'job_id': job_id, 'error': 'job id not found'}, 404


def get_output_stream(proc):
    retval = ""
    for line in iter(proc.stdout.readline, ''):
        retval += line.rstrip() + "\n"
    return retval


def get_job_output(job_id):
    if job_id in job_watchers:
        status = job_watchers[job_id].poll()
        if status is None:
            return "Job is still running, try again later.", 404
        elif status == 0:
            return get_output_stream(job_watchers[job_id]), 200
        else:
            return "Job failed!\n" + get_output_stream(job_watchers[job_id]), 500
    else:
        return "ID ot found!", 404

logging.basicConfig(level=getattr(logging, 'INFO', None))

api_args = {'auth_url': utils.get_os_env('AUTH_URL'),
            'tokeninfo_url': utils.get_os_env('TOKENINFO_URL'),
            'oauth2_scope': utils.get_os_env('OAUTH2_SCOPE')}
webapp = connexion.App(__name__, port=8000, debug=True, server='gevent')
webapp.add_api('swagger.yaml', arguments=api_args)
application = webapp.app

if __name__ == '__main__':
    webapp.run()
