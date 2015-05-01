#!/usr/bin/env python

# Copyright 2015 University of Chicago

import sys
import argparse
import logging
import pytz
import os
import pwd
import grp
import datetime

import elasticsearch
import elasticsearch.helpers


ES_NODES = ['uct2-es-head.mwt2.org:9200', 'uct2-es-door.mwt2.org:9200']
TZ_NAME = "US/Central"
TIMEZONE = pytz.timezone(TZ_NAME)


def get_es_client():
    """ Instantiate DB client and pass connection back """
    return elasticsearch.Elasticsearch(hosts=ES_HOST,
                                       retry_on_timeout=True,
                                       max_retries=10,
                                       timeout=300)


def create_record(dirpath, date, index=None):
    """
    Query directory at dirpath for information and store information in ES

    :param dirpath: string storing path to file
    :param date: datetime.date with date to use
    :param inde: ES index for records
    :return: dictionary with record if successful, empty dict otherwise
    """
    if not os.path.isdir(dirpath):
        return {}
    if not index:
        index = "stash-space-{0}".format(date.year, date.month)
    dir_info = os.stat(filepath)
    uid = dir_info.st_uid
    gid = dir_info.st_gid
    ctime = datetime.datetime.fromtimestamp(dir_info.st_ctime, TIMEZONE)
    mtime = datetime.datetime.fromtimestamp(dir_info.st_mtime, TIMEZONE)
    record_fields = {'@timestamp': date.isoformat(),
                     'size': dir_info.st_size,
                     'ctime': ctime,
                     'mtime': mtime,
                     'user': pwd.getpwuid(uid),
                     'group': grp.getgrgid(gid),
                     'path': dirpath}
    record = {'_index': index,
              '_source': record_fields,
              '_op_type': 'index',
              '_type': 'interval_record'}
    return record


def traverse_directory(dirpath, index=None):
    """
    Traverse subdirectories and create a set of records
    with space usage
    :param dirpath: path to directory to
    :return: Nothing
    """
    current_date = timezone.localize(datetime.date.today())

    if not os.path.isdir(dirpath):
        return
    records = []
    for root, dirs, files in os.walk(dirpath):
        record = create_record(root, current_date, index)
        if record:
            records.append(record)
    save_records(records)

def save_records(records=None):
    """
    Save a job record to ES
    """
    es_client = get_es_client()
    elasticsearch.helpers.bulk(es_client,
                               records,
                               stats_only=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get space usage on a given '
                                                 'filesystem and store in ES')
    parser.add_argument('--index', dest='index', default=None,
                        help='ES index to store records in')
    parser.add_argument("directory", default=None, required=True,
                        help="Directory to examine")
    args = parser.parse_args(sys.argv[1:])
    if not os.path.isdir(args.directory):
        sys.stderr.write("{0} must be a directory\n".format(atgs.directory))
        sys.exit(1)
    traverse_directory(args.directory, args.index)
