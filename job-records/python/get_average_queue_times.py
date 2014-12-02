#!/usr/bin/env python

import sys
import datetime
import argparse

import elasticsearch


ES_MASTER = 'http://uct2-es-head.mwt2.org:9200'

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

    queue_time = 0
    calculated_queue_time = 0
    week = day.isocalendar()[1]
    # want to get the week before and after since
    index = 'jobsarchived_2014_{0}'.format(week - 1)
    index += ',jobsarchived_2014_{0}'.format(week)
    results = es.search(index=index,
                        body={"filter":
                                  {"range":
                                        {"MODIFICATIONTIME":
                                             {"gte": day.isoformat(),
                                              "lte": day.isoformat()}}}},
                        fields="queue_time,STARTTIME,CREATIONTIME",
                        size=1000)
    queue_time = 0
    calculated_queue_time = 0
    for document in results['hits']['hits']:
        if 'fields' in document:
            if ('queue_time' not in document['fields'] or
                'STARTTIME' not in document['fields'] or
                'CREATIONTIME' not in document['fields']):
                print document
                continue
            queue_time += int(document['fields']['queue_time'][0])
            start_time = datetime.datetime.strptime(document['fields']['STARTTIME'][0], "%Y-%m-%dT%H:%M:%S+00:00")
            creation_time = datetime.datetime.strptime(document['fields']['CREATIONTIME'][0], "%Y-%m-%dT%H:%M:%S+00:00")
            delta = (start_time - creation_time)
            # total_seconds for timedelta not present before python 2.7
            calculated_queue_time += (delta.microseconds +
                                      (delta.seconds +
                                       delta.days * 24 * 3600) * 10**6) / 10**6
    doc_count = float(results['hits']['total'])
    return queue_time / doc_count, calculated_queue_time / doc_count, doc_count

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
    while current_date <= end_date:
        result = calculate_average_queue_time(current_date, es)
        if result != (None, None, None):
            sys.stdout.write("{0},{1},{2}\n".format(result))
        current_date += datetime.timedelta(days=1)

    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create a condor submit file for processing job log data.')
    parser.add_argument('--startdate', dest='start_date', default=datetime.date.today().isoformat(),
                        help='Date to start processing logs from')
    parser.add_argument('--enddate', dest='end_date', default=datetime.date.today().isoformat(),
                        help='Date to stop processing logs')
    args = parser.parse_args(sys.argv[1:])
    args.start_date = parse_date(args.start_date)
    args.end_date = parse_date(args.end_date)
    es = elasticsearch.Elasticsearch(ES_MASTER)
    get_average_queue_times(args.start_date, args.end_date, es)

