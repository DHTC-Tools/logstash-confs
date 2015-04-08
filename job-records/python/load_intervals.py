#!/usr/bin/env python


# Copyright 2014 University of Chicago

import os
import datetime
import glob
import sys
import re
import argparse
import pytz
import logging
import json
import time

import elasticsearch
from elasticsearch import helpers

VERSION = '0.2'
TZ_NAME = 'UTC'
ES_HOST = ['uct2-es-door.mwt2.org', 'uct2-es-head.mwt2.org']
TIMEZONE = pytz.timezone(TZ_NAME)


def save_records(es_client=None, records=None):
    """
    Save a job record to ES
    """
    if not es_client or not records:
        return
    helpers.bulk(es_client,
                 records,
                 stats_only=False)


def load_data(directory, es_client):
    """
    Load data from a directory with interval data in files named
    part-*

    :param directory: path to directory
    :param es_client: ES client object to use
    :return: Nothing
    """
    if not os.path.isdir(directory):
        return
    doc_count = 0
    records = []
    for filename in glob.glob(os.path.join(directory, "part-*")):
        sys.stdout.write("Loading {0} file\n".format(filename))
        for line in open(filename):
            record = parse_record(line)
            if record != {}:
                records.append(record)
                doc_count += 1
            if (doc_count % 5000) == 0:
                save_records(es_client, records)
                records = []
                sys.stdout.write("Wrote {0} records\n".format(doc_count))
        if not records:
            save_records(es_client, records)
            records = []
            sys.stdout.write("Wrote {0} records\n".format(doc_count))


def parse_record(line):
    """
    Parse a line containing an interval records into a dictionary
    that can be fed into ES

    :param line: string with data fields for the record
    :return: dictionary that can be fed to the ES bulk helper
    """

    record = {}
    record_fields = {}
    fields = line.split("\t")
    event_time = datetime.datetime.fromtimestamp(float(fields[0])/1000.0,
                                                 TIMEZONE)
    record_fields['@timestamp'] = event_time.isoformat()
    record_fields['CRTIME'] = event_time.isoformat()
    record_fields['PANDAID'] = int(fields[1])
    record_fields['CLOUD'] = fields[2].strip()
    record_fields['COMPUTINGSITE'] = fields[3].strip()
    record_fields['PRODSOURCELABEL'] = fields[4].strip()
    raw_times = fields[5]
    times = []
    if raw_times != '{}':
        for x in re.finditer('\((\w+),(\d+)\)', raw_times):
            times.append({'state': x.group(1).strip(),
                                    'time': x.group(2)})
    record_fields['times'] = times
    record_fields['SKIPPED'] = int(fields[6])
    record_fields['SORTED'] = int(fields[7].strip())
    year, iso_week, _ = event_time.isocalendar()
    record['_index'] = "interval-data-{0}-{1:0>2}".format(year, iso_week)
    record['_source'] = record_fields
    record['_op_type'] = 'index'
    record['_type']  = 'interval_record'
    return record


def get_es_client():
    """ Instantiate DB client and pass connection back """
    return elasticsearch.Elasticsearch(host=ES_HOST)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Load interval data from a directory into ES')
    parser.add_argument('--location', dest='location', default=None,
                        help='Location of directory to place submit files')
    args = parser.parse_args(sys.argv[1:])
    if args.location is None:
        sys.stderr.write("location must be given\n")
    client = get_es_client()
    load_data(args.location, client)
