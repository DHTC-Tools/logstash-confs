#!/usr/bin/env python

# Copyright 2014 University of Chicago

import pwd
import os
import datetime
import sys

import pytz
import htcondor
import elasticsearch
from elasticsearch import helpers

VERSION = '0.1'
JOB_STATUS = {0: 'Unexpanded',
              1: 'Idle',
              2: 'Running',
              3: 'Removed',
              4: 'Completed',
              5: 'Held',
              6: 'Submission Error'}
JOB_ATTRS = ['ProcId',
             'ClusterId', 
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
TZ_NAME = 'US/Central'
ES_HOST = 'uct2-es-door.mwt2.org'


def query_scheduler(client=None):
    """
    Query a condor schedd instance and then update elastic search db with
    info obtained
    """
    if client is None:
        return 
    schedd = htcondor.Schedd()
    jobs = schedd.query("True", JOB_ATTRS)
    user_job_status = {}
    timezone = pytz.timezone(TZ_NAME)
    current_time = timezone.localize(datetime.datetime.now())
    job_records = []
    for job in jobs:
        status = JOB_STATUS[job['JobStatus']]
        if status in user_job_status:
            user_job_status[status] += 1
        else:
            user_job_status[status] = 1
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
        if 'host' not in user_job_status:
            user_job_status['host'] = submit_host
        job_records.append(job_record)
    save_job_records(client, job_records)
    user_job_status['@timestamp'] = current_time.isoformat()
    save_collector_status(client, user_job_status)


def save_job_records(client=None, records=None):
    """
    Save a job record to ES
    """
    if client is None or records is None or records == []:
        return
    helpers.bulk(client, records, index='osg-connect-job-details', doc_type='job_record', stats_only=True)
    # client.index(index='osg-connect-jobs', doc_type='job_record', body=record)


def save_collector_status(client, record):
    """
    Save collector status to ES
    """
    if client is None or record is None or record == {}:
        return
    record_time = record['@timestamp']
    for status in record:
        es_record = {'jobs': record[status],
                     'status': status,
                     'host': record['host'],
                     '@timestamp': record_time}
        client.index(index='osg-connect-schedd-state', doc_type='schedd_status', body=es_record)


def get_es_client():
    """ Instantiate DB client and pass connection back """

    client = elasticsearch.Elasticsearch(host=ES_HOST)
    return client

if __name__ == '__main__':
    es_client = get_es_client()
    query_scheduler(es_client)
