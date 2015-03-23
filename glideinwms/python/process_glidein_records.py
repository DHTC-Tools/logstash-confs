#!/usr/bin/env python

import sys
import datetime
import argparse
import logging
import pytz
import os
import glob
import xml.etree.ElementTree as ET
import dateutil.parser

import elasticsearch
from elasticsearch import helpers

ES_NODES = 'uct2-es-door.mwt2.org'
VERSION = '0.1'
metric_list = ['CwdFreeKb',
               'CwdMinKb',
               'TmpFreeKb',
               'TmpMinKb',
               'TmpWritable',
               'MaxMemMBs',
               'GLIDEIN_CPUS',
               'GLIDEIN_SiteWMS',
               'GLIDEIN_SiteWMS_JobId',
               'GLIDEIN_SiteWMS_Slot',
               'GLIDEIN_SiteWMS_Queue',
               'AutoShutdown',
               'CondorDuration',
               'TotalJobsNr',
               'TotalJobsTime',
               'goodZJobsNr',
               'goodZJobsTime',
               'goodNZJobsNr',
               'goodNZJobsTime',
               'badSignalJobsNr',
               'badSignalJobsTime',
               'badOtherJobsNr',
               'badOtherJobsNr',
               'CondorKilled']
env_list = ['glidein_factory',
            'glidein_name',
            'glidein_entry',
            'condorg_cluster',
            'condorg_subcluster',
            'glidein_credential_id',
            'condorg_schedd',
            'client_name',
            'client_group',
            'user',
            'arch',
            'os',
            'hostname',
            'cwd']
TIMEZONE = "US/Central"

def get_es_client():
    """
    Function to instantiate an ES client and return object reference for
    further use

    :return: Elasticsearch client instance
    """
    return elasticsearch.Elasticsearch(ES_NODES)


def validate_date(arg):
    """
    Validate that text string provided is a valid date
    """
    if arg is None or len(arg) != 8:
        return None
    year = arg[0:4]
    month = arg[4:6]
    day = arg[6:8]
    try:
        year = int(year)
        month = int(month)
        day = int(day)
    except ValueError:
        return None
    if year < 2000 or year > 2038:
        return None
    if month < 1 or month > 12:
        return None
    if day < 1 or day > 31:
        return None
    try:
        temp = datetime.date(year, month, day)
    except ValueError:
        return None
    return temp


def get_xml_info(filename):
    """
    Get the relevant metrics and env data from xml files generated from
    gwms factory information

    :param filename: name of xml file to parse
    :return: a dictionary with values for env and metrics information
    """
    if not os.path.isfile(filename):
        return {}
    tree = ET.parse(filename)
    root = tree.getroot()
    record = {}
    for metric in root.getiterator('metric'):
        if metric.get('name') in metric_list:
            record[metric.get('name')] = metric.text
        if metric.get('name') == 'CwdFreeKb':
            timestamp = dateutil.parser.parse(metric.get('ts'))
            iso_year, iso_week, iso_weekday = timestamp.isocalendar()
            record['@timestamp'] = timestamp
            record['isoyear'] = iso_year
            record['isoweek'] = iso_week
            record['isoweekday'] = iso_weekday
    for env in root.getiterator('env'):
        if env.get('name') in env_list:
            record[env.get('name')] = env.text
    return record

def save_job_records(client=None, records=None, index=None):
    """
    Save job records to ES

    :param client: an instantiated ES client
    :param records: iterator with records to insert
    :param index: string with index in ES to insert into
    """
    if not client or not records or not index:
        return
    helpers.bulk(client,
                 records,
                 index=index,
                 doc_type='job_record',
                 stats_only=False)


def main():
    """
    Handle argument parsing and dispatch to appropriate functions
    """
    parser = argparse.ArgumentParser(description='Process gwms records')
    parser.add_argument('--location', dest='location', default=None,
                        help='Location of directory with glidein records')
    parser.add_argument('--startdate', dest='start_date', default=None,
                        help='Date to start processing logs')
    parser.add_argument('--enddate', dest='end_date', default=None,
                        help='Date to stop processing logs')
    args = parser.parse_args(sys.argv[1:])
    if args.location is None:
        logging.error("Location of Glidein files must be specified")
    start_date = validate_date(args.start_date)
    if start_date is None:
        logging.error("startdate must be in YYYYMMDD format, "
                      "got {0}\n".format(args.start_date))
        sys.exit(1)
    end_date = validate_date(args.end_date)
    if end_date is None:
        logging.error("enddate must be in YYYYMMDD format, "
                      "got {0}\n".format(args.end_date))
        sys.exit(1)
    es_client = get_es_client()
    records = []
    current_week_date = start_date
    end_datetime = datetime.datetime.combine(end_date, datetime.time(0, 0, 0))
    timezone = pytz.timezone(TIMEZONE)
    end_datetime = timezone.localize(end_datetime)
    for filename in glob.glob(os.path.join(args.location, '*.xml')):
        record = get_xml_info(filename)
        records.append(record)
    while current_week_date < end_date:
        iso_year, iso_week, iso_weekday = current_week_date.isocalendar()
        index = "gwms-job-details-{0}-{1}".format(iso_year, iso_week)
        new_records = []
        insert_records = []
        for record in records:
            if record['isoweek'] == iso_week and record['isoyear'] == iso_year:
                if record['@timestamp'] > end_datetime:
                    continue
                del record['isoweek']
                del record['isoyear']
                del record['isoweekday']
                insert_records.append(record)
            elif record['isoyear'] > iso_year:
                new_records.append(record)
            elif record['isoweek'] > iso_week and record['isoyear'] == iso_year:
                new_records.append(record)
        save_job_records(es_client, insert_records, index)
        records = new_records
        current_week_date += datetime.timedelta(days=(8 - iso_weekday))


if __name__ == '__main__':
    main()
