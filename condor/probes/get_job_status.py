#!/usr/bin/env python

# Copyright 2014-2015 University of Chicago

import argparse
import datetime
import sys

import pytz
import htcondor
import elasticsearch
from elasticsearch import helpers

VERSION = '0.3'
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
ES_HOST = ['uct2-es-door.mwt2.org', 'uct2-es-head.mwt2.org']
ES_JOB_DETAILS_INDEX_BASE = 'osg-connect-job-details'
ES_SCHEDD_STATE_INDEX_BASE = 'osg-connect-schedd-state'


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


def query_scheduler(schedd_index_base, job_detail_index_base):
    """
    Query a condor schedd instance and then update elastic search db with
    info obtained

    :param schedd_index_base: base for index name for schedd state records
    :param job_detail_index_base: base for index name for job detail records
    """
    client = get_es_client()
    if not client:
        return
    if not (schedd_index_base and job_detail_index_base):
        return
    schedd = htcondor.Schedd()
    jobs = schedd.query("True", JOB_ATTRS)
    user_job_status = {}
    timezone = pytz.timezone(get_timezone())
    current_time = timezone.localize(datetime.datetime.now())
    job_records = []
    current_host = None
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
        if current_host is None:
            current_host = submit_host
        job_records.append(job_record)

    save_job_records(client, job_detail_index_base, job_records)
    save_collector_status(client,
                          schedd_index_base,
                          user_job_status,
                          current_host,
                          current_time.isoformat())


def save_job_records(client=None, index_base=None, records=None):
    """
    Save a job record to ES

    :param client: ES client to use for connections
    :param index_base: base for index name
    :param records: list of records to insert into ES index
    """
    if not (client and records and records):
        return
    if not index_base:
        index_base = ES_JOB_DETAILS_INDEX_BASE
    timezone = pytz.timezone(get_timezone())
    current_time = timezone.localize(datetime.datetime.now())
    year, week, _ = current_time.isocalendar()
    index_name = '{0}-{1}-{2}'.format(index_base, year, week)
    print index_name
    helpers.bulk(client,
                 records,
                 index=index_name,
                 doc_type='job_record',
                 stats_only=True)


def save_collector_status(client, index_base=None, record=None, host=None, time=None):
    """
    Save collector status to ES
    :param client: ES client to use for connections
    :param index_base: base for index name
    :param record: dictionary with jobs states and number of jobs in that state
    :param host: hostname of the schedd that is being queried
    :param time: timestamp for document
    """
    if not (client and record and record):
        return
    if not index_base:
        index_base = ES_SCHEDD_STATE_INDEX_BASE
    timezone = pytz.timezone(get_timezone())
    current_time = timezone.localize(datetime.datetime.now())
    index_name = '{0}-{1}'.format(index_base, current_time.isocalendar()[0])
    for status in record:

        es_record = {'jobs': record[status],
                     'status': status,
                     'host': host,
                     '@timestamp': time}
        print index_name
        client.index(index=index_name, doc_type='schedd_status', body=es_record)



def get_es_client():
    """ Instantiate DB client and pass connection back """
    return elasticsearch.Elasticsearch(hosts=ES_HOST,
                                       retry_on_timeout=True,
                                       max_retries=10,
                                       timeout=90)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create  '
                                                 'for processing job log data.')
    parser.add_argument('--schedd-index-base', dest='schedd_index_base',
                        default=ES_SCHEDD_STATE_INDEX_BASE,
                        help='Base name to use for indexing schedd data')
    parser.add_argument('--job-index-base', dest='job_index_base',
                        default=ES_JOB_DETAILS_INDEX_BASE,
                        help='Base name to use for indexing job history data')

    args = parser.parse_args(sys.argv[1:])
    es_client = get_es_client()
    query_scheduler(args.schedd_index_base, args.job_index_base)
