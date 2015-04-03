#!/usr/bin/env python

import datetime
import argparse
import sys
import logging
import pytz

import elasticsearch
import elasticsearch.helpers

ES_NODES = 'uct2-es-door.mwt2.org'
VERSION = '0.1'
SOURCE_INDEX = 'osg-connect-job-details'


def get_start_week(start_date):
    """
    Return a datetime that starts at the beginning of the iso week that
    start_date falls in (e.g. if start_date is in day 5 of an iso week
    return a datetime object from 5 days ago)

    :param start_date: an UTC localized datetime object to use
    :return: an UTC localized datetime that
    """

    iso_datetime = start_date - datetime.timedelta(days=start_date.isoweekday())
    return iso_datetime


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
        utc = pytz.utc
        temp = utc.localize(datetime.datetime(year, month, day, 0, 0, 0))
    except ValueError:
        return None
    return temp


def reindex(source_index, target_index, start_date, end_date, client):
    """
    Reindex documents that occur between start_date and end_date
    from source index to target index

    :param client: instantiated ES client to use
    :param source_index: source index for documents
    :param target_index: destination index for documents that match
    :param start_date: UTC localized datetime that documents need to occur after
    :param end_date: UTC localized datetime that documents need to occur before
    :return: tuple of (# of successes, error messages) indicating any issues
    """

    utc = pytz.utc
    start_time = utc.localize(datetime.datetime.combine(start_date, datetime.time(0, 0, 0)))
    end_time = utc.localize(datetime.datetime.combine(end_date, datetime.time(0, 0, 0)))
    range_query = {"query": {
        "filtered": {
            "filter": {
                "bool": {
                    "must": [
                        {"range":
                             {"@timestamp":
                                  {"gte": start_time.isoformat(),
                                   "lt": end_time.isoformat()}}}]}}}}}
    results = elasticsearch.helpers.reindex(client,
                                            source_index,
                                            target_index,
                                            range_query,
                                            scroll='30m')
    return results


def get_es_client():
    """ Instantiate DB client and pass connection back """
    return elasticsearch.Elasticsearch(hosts=ES_NODES,retry_on_timeout=True,max_retries=10,timeout=300) 


def scan_and_reindex(start_date=None, end_date=None, client=None):
    """
    Iterate through weeks between start and end date and
    reindex documents to a weekly index

    :param start_date: date to start reindexing
    :param end_date: date to end indexing
    :param client: instantiated ES client to use
    :return: None
    """
    current_date = get_start_week(start_date)
    while current_date < end_date:
        iso_year, iso_week, _ = current_date.isocalendar()
        weekly_index = "{0}-{1}-{2:0>2}".format('osg-connect-job-details',
                                                iso_year,
                                                iso_week)
        week_end_date = current_date + datetime.timedelta(days=7)
        results = reindex(SOURCE_INDEX,
                          weekly_index,
                          current_date,
                          week_end_date,
                          client)
        logging.warning("{0}".format(results))
        current_date += datetime.timedelta(days=7)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reindex events from ' +
                                                 'osg-connect-job-details ' +
                                                 'to weekly indices')
    parser.add_argument('--start-date',
                        dest='start_date',
                        default=None,
                        required=True,
                        help='Reindex events that occur on this day or after')
    parser.add_argument('--end-date',
                        dest='end_date',
                        default=None,
                        help='Reindex events that occur before this day')
    args = parser.parse_args(sys.argv[1:])
    start_date = validate_date(args.start_date)
    end_date = validate_date(args.end_date)
    client = get_es_client()
    scan_and_reindex(start_date, end_date, client)
