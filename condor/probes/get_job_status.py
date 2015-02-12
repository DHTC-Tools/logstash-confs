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
             'CumulativeSuspensionTime']
TZ_NAME = 'US/Central'

def query_scheduler(client = None):
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
    current_time =  timezone.localize(datetime.datetime.now())
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
        job_record['timestamp'] = current_time.isoformat()
        if status == 'Idle':
            queue_time = datetime.datetime.fromtimestamp(job_record['QDate'])
            queue_wait = current_time - timezone.localize(queue_time)
            job_record['QueueTime'] = queue_wait.seconds
        job_records.append(job_record)
    save_job_records(client, job_records)
    user_job_status['timestamp'] = current_time.isoformat()
    save_collector_status(client, user_job_status)

def save_job_records(client = None, records = None):
    """
    Save a job record to ES
    """
    if client is None or records is None or records == []:
        return
    results = helpers.bulk(client, records, index='osg-connect-job-details', doc_type='job_record', stats_only=True)
    #client.index(index='osg-connect-jobs', doc_type='job_record', body=record)

def save_collector_status(client, record):
    """
    Save collector status to ES
    """
    if client is None or record is None or record == {}:
        return
    record_time = record['timestamp']
    del record['timestamp']
    for status in record:
        es_record = {}
        es_record['jobs'] = record[status]
        es_record['status'] = status
        es_record['timestamp'] = record_time
        client.index(index='osg-connect-schedd-state', doc_type='schedd_status', body=es_record)

def get_es_client():
    """ Instantiate DB client and pass connection back """

    client = elasticsearch.Elasticsearch(host='uct2-es-door.mwt2.org')
    return client

if __name__ == '__main__':
    client = get_es_client()
    query_scheduler(client)
