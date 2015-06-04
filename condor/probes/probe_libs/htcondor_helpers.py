# Copyright 2015 University of Chicago
# Available under Apache 2.0 License

import socket
import datetime

import pytz
import htcondor

JOB_STATUS = {0: 'Unexpanded',
              1: 'Idle',
              2: 'Running',
              3: 'Removed',
              4: 'Completed',
              5: 'Held',
              6: 'Submission Error'}
JOB_ATTRS = ['ProcId',
             'ClusterId',
             'GlobalJobId',
             'JobStatus',
             'User',
             'ProjectName',
             'QDate',
             'JobStartDate',
             'CommittedTime',
             'RemoteWallClockTime',
             'RemoteSysCpu',
             'RemoteUserCpu',
             'MATCH_EXP_JOBGLIDEIN_ResourceName',
             'CumulativeSuspensionTime']


def get_timezone():
    """
    Query the system and return timezone on RHEL/SL systems

    :return: a string with the timezone for the system
    """
    try:
        for line in open('/etc/sysconfig/clock'):
            field, value = line.split('=')
            if field.strip() == 'ZONE':
                return value.replace('"', '').strip()
        return ""
    except IOError:
        return ""


def get_local_schedds():
    """
    Gets the local schedds and returns classads for them

    :return:  a list of classads for local schedds
    """
    schedd_list = []
    temp_list = htcondor.Collector().locateAll(htcondor.DaemonTypes.Schedd)
    local_hostname = socket.getfqdn()
    for schedd in temp_list:
        if 'Name' not in schedd:
            continue
        if local_hostname in schedd['Name']:
            schedd_list.append(schedd)
    return schedd_list

def schedd_states(schedd_classad):
    """
    Returns information about the number of jobs in each job state for a schedd

    :param schedd_classad: classad for schedd to query
    :return: a dictionary with job states as keys and number of jobs in
             given state as a value
    """
    return {'Running': schedd_classad['TotalRunningJobs'],
            'Idle': schedd_classad['TotalIdleJobs'],
            'Held': schedd_classad['TotalHeldJobs'],
            'Removed': schedd_classad['TotalRemovedJobs']}

def get_schedd_jobs(schedd_classad=None, job_attrs=JOB_ATTRS):
    """
    Queries local schedd to get job classads

    :param schedd_classad: classad for schedd to query
    :return: a list of dicts containing job classads
    """
    job_records = []
    schedd = htcondor.Schedd(schedd_classad)
    timezone = pytz.timezone(get_timezone())
    current_time = timezone.localize(datetime.datetime.now())
    jobs = schedd.query("True", job_attrs)
    for job in jobs:
        status = JOB_STATUS[job['JobStatus']]
        job_record = {}
        for attr in JOB_ATTRS:
            try:
                job_record[attr] = job[attr]
            except KeyError:
                # a lot of attributes will be missing if job is not running
                pass
        job_record['JobStatus'] = status
        job_record['@timestamp'] = current_time.isoformat()
        if status == 'Idle':
            queue_time = datetime.datetime.fromtimestamp(job_record['QDate'])
            queue_wait = current_time - timezone.localize(queue_time)
            job_record['QueueTime'] = queue_wait.seconds
        if 'MATCH_EXP_JOBGLIDEIN_ResourceName' in job_record:
            job_record['Resource'] = job_record['MATCH_EXP_JOBGLIDEIN_ResourceName']
            if job_record['Resource'] == "uc3-mon.mwt2.org":
                job_record['Resource'] = 'UC3'
            del job_record['MATCH_EXP_JOBGLIDEIN_ResourceName']
        (user, submit_host) = job_record['User'].split('@')
        job_record['User'] = user
        job_record['SubmitHost'] = submit_host
        if current_host is None:
            current_host = submit_host
        job_records.append(job_record)
    return job_records

