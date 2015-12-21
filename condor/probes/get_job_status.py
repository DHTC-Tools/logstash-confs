#!/usr/bin/env python

# Copyright 2015 University of Chicago
# Available under Apache 2.0 License

import argparse
import datetime
import sys
import socket

import pytz
import elasticsearch
from elasticsearch import helpers

import probe_libs.htcondor_helpers

VERSION = '0.4.1'
ES_HOST = ['uct2-es-door.mwt2.org', 'uct2-es-head.mwt2.org']
ES_JOB_DETAILS_INDEX_BASE = 'osg-connect-job-details'
ES_SCHEDD_STATE_INDEX_BASE = 'osg-connect-schedd-state'


def query_scheduler(schedd_index_base, job_detail_index_base, schedd_base_name):
    """
    Query a condor schedd instance and then update elastic search db with
    info obtained

    :param schedd_index_base: base for index name for schedd state records
    :param job_detail_index_base: base for index name for job detail records
    :param schedd_base_name:
    """
    client = get_es_client()
    if not client:
        return
    if not (schedd_index_base and job_detail_index_base):
        return
    timezone = pytz.timezone(probe_libs.htcondor_helpers.get_timezone())
    current_time = timezone.localize(datetime.datetime.now())
    current_host = socket.getfqdn()
    schedds = probe_libs.htcondor_helpers.get_local_schedds(schedd_base_name)
    for schedd in schedds:
        job_records = probe_libs.htcondor_helpers.get_schedd_jobs(schedd)
        states = probe_libs.htcondor_helpers.schedd_states(schedd)
        save_job_records(client, job_detail_index_base, job_records)
        save_schedd_status(client,
                           schedd_index_base,
                           states,
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
    timezone = pytz.timezone(probe_libs.htcondor_helpers.get_timezone())
    current_time = timezone.localize(datetime.datetime.now())
    year, week, _ = current_time.isocalendar()
    index_name = '{0}-{1}-{2}'.format(index_base, year, week)
    helpers.bulk(client,
                 records,
                 index=index_name,
                 doc_type='job_record',
                 stats_only=True)


def save_schedd_status(client, index_base=None, record=None, host=None, time=None):
    """
    Save schedd status to ES
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
    timezone = pytz.timezone(probe_libs.htcondor_helpers.get_timezone())
    current_time = timezone.localize(datetime.datetime.now())
    index_name = '{0}-{1}'.format(index_base, current_time.isocalendar()[0])
    for status in record:
        es_record = {'jobs': record[status],
                     'status': status,
                     'host': host,
                     '@timestamp': time}
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
    parser.add_argument('--schedd-base-name', dest='schedd_base_name',
                        required=True,
                        help='String that all schedd names must include (e.g. local.host.com)')
    parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)
    args = parser.parse_args(sys.argv[1:])
    es_client = get_es_client()
    query_scheduler(args.schedd_index_base, args.job_index_base, args.schedd_base_name)
