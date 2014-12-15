#!/usr/bin/env python

import sys
import datetime
import csv
import logging

import elasticsearch
import elasticsearch.helpers


ES_NODES = ['uct2-es-head.mwt2.org:9200', 'uct2-es-door.mwt2.org:9200']

def get_panda_ids():
    """
    get panda ids from CSV files and return a set with them
    :return:
    """

    id_set = set()
    input_file = open('JobsForTheDay.csv'. 'r')
    reader = csv.reader(file=input_file)
    for row in reader:
        id_set.add(row[1])
    return id_set



def find_ids(day=datetime.date(2014, 7, 14), es=None):
    """
    Look for any panda ids missing from specificed date

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
    results = elasticsearch.helpers.scroll(es,
                                           index=index,
                                           body={"filter":
                                                     {"numeric_range":
                                                          {"MODIFICATIONTIME":
                                                               {"gte": day.isoformat(),
                                                                "lte": day.isoformat()}}}},
                                           fields="PANDAID")
    calculated_queue_time = 0
    found_ids = set()
    for document in results['hits']['hits']:
        if 'fields' not in document:
                continue
        panda_id = int(document['fields']['PANDAID'])
        found_ids.add(panda_id)
    return found_ids


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
            sys.stdout.write("{0},{1},{2}\n".format(*result))
        current_date += datetime.timedelta(days=1)


if __name__ == "__main__":
    args.end_date = parse_date(args.end_date)
    es = elasticsearch.Elasticsearch(ES_NODES)
    panda_ids = get_panda_ids()
    es_ids = find_ids(day = datetime.date(2014, 7, 14), es)
    sys.stdout.write("Number of ids in Hadoop: {0}\n".format(len(panda_ids)))
    sys.stdout.write("Number of ids in ES: {0}\n".format(len(es_ids)))




