#!/usr/bin/env python

import sys
import datetime
import time
import argparse
import logging
import csv
import pytz

import elasticsearch
import elasticsearch.helpers


ES_NODES = ['uct2-es-head.mwt2.org:9200', 'uct2-es-door.mwt2.org:9200']
TZ_NAME = "UTC"

def parse_date(date=None):
    """
    Parse a string in YYYY-MM-DD format into a datetime.date object.
    Throws ValueError if input is invalid

    :param date: string in YYYY-MM-DD format giving a date
    :return: a datetime.date object corresponding to the date given
    """
    if date is None:
        raise ValueError
    fields = date.split('-')
    if len(fields) != 3:
        raise ValueError
    return datetime.date(year=int(fields[0]),
                         month=int(fields[1]),
                         day=int(fields[2]))


def get_week_start(date=None):
    """
    Return a datetime corresponding to the start of the week for the given date
    E.g. if tuesday 7/8/2014 is passed in, monday 7/7/2014 00:00:00 would
    be returned
    """
    if date is None:
        start_date = datetime.date.today()
    else:
        start_date = date
    week_day = start_date.isoweekday()
    if week_day != 7 and week_day != 0:
        week_start = start_date - datetime.timedelta(days=week_day)
    else:
        week_start = start_date
    return week_start


def calculate_average_queue_time(day=datetime.date.today(), es=None):
    """
    Calculate the average queue_time (STARTTIME - CREATIONTIME) for given a
    date, selects records by querying against MODIFICATIONTIME

    :param day: Date object specifying date to query
    :param es:  elasticsearch connection to use
    :return: tuple with average queue time for specified date, first element
             uses queue_time column second element calculates queue_time
             using STARTTIME and CREATIONTIME columns, the third element is
             the number of documents returned in the search
    """
    if es is None:
        return None, None, None

    week = day.isocalendar()[1]
    # want to get the week before and after since
    index = 'jobsarchived_2014_{0}'.format(week - 1)
    index += ',jobsarchived_2014_{0}'.format(week)
    utc = pytz.utc
    start_time = utc.localize(datetime.datetime.combine(day, datetime.time(0, 0, 0)))
    end_day = day + datetime.timedelta(days=1)
    end_time = utc.localize(datetime.datetime.combine(end_day, datetime.time(0, 0, 0)))
    results = es.search(body=
                        {"query": {
                            "filtered": {
                                "filter": {
                                    "bool": {
                                        "must": [
                                            {"range":
                                                 {"MODIFICATIONTIME":
                                                      {"gte": start_time,
                                                       "lt": end_time}}},
                                            {"exists": {"field": "CREATIONTIME"}},
                                            {"exists": {"field": "STARTTIME"}},
                                            {"exists": {"field": "queue_time"}}]}}}},
                         "size": 0,
                         "aggs": {
                             "queue_avg":
                                 {"avg":
                                       {"field": "queue_time"}},
                             "script_avg":
                                 {"avg":
                                       {"script": "doc['STARTTIME'].value - doc['CREATIONTIME'].value"}}}},
                        size=0,
                        index=index)
    doc_count = results['hits']['total']
    if doc_count == 0:
        queue_time = 'NA'
        script_time = 'NA'
    else:
        queue_time = results['aggregations']['queue_avg']["value"]
        script_time = results['aggregations']['script_avg']["value"] / 1000
            
    if doc_count == 0:
        logging.warn("No documents for {0}".format(day.isoformat()))
        return 0, 0, 0
    return queue_time, script_time, doc_count


def get_average_queue_times(start_date, end_date, es=None):
    """
    Calculate and print the average queue
    :param start_date: Date object giving the first day in time range to use
    :param end_date:   Date object giving the last day in time range to use
    :param es:         elasticsearch object to use
    :return:           Nothing, (prints out results to stdout)
    """
    if es is None:
        return
    current_date = start_date
    output_file = open('averages.csv', 'w')
    writer = csv.writer(output_file)
    writer.writerow(['Date', 'queue_time average', 'STARTTIME - CREATIONTIME average', 'documents'])
    while current_date <= end_date:
        result = calculate_average_queue_time(current_date, es)
        if result != (None, None, None):
            sys.stdout.write("{0},{1},{2},{3}\n".format(current_date.isoformat(),*result))
            logging.info("{0},{1},{2},{3}\n".format(current_date.isoformat(),*result))
            writer.writerow([current_date.isoformat()] + list(result))
        current_date += datetime.timedelta(days=1)
    output_file.close()


if __name__ == "__main__":
    logging.basicConfig(filename='average.log', level=logging.WARN)
    parser = argparse.ArgumentParser(description='Create a condor submit file for processing job log data.')
    parser.add_argument('--startdate', dest='start_date', default=datetime.date.today().isoformat(),
                        help='Date to start processing logs from')
    parser.add_argument('--enddate', dest='end_date', default=datetime.date.today().isoformat(),
                        help='Date to stop processing logs')
    args = parser.parse_args(sys.argv[1:])
    args.start_date = parse_date(args.start_date)
    args.end_date = parse_date(args.end_date)
    es = elasticsearch.Elasticsearch(ES_NODES)
    get_average_queue_times(args.start_date, args.end_date, es)

