#!/usr/bin/env python

__author__ = 'sthapa'

import time
import datetime
import argparse
import sys
import logging
import pytz

import elasticsearch
import elasticsearch.helpers
import pymongo

MONGO_SERVER = 'db.mwt2.org'
MONGO_SERVER_PORT = 27017
ES_NODES = ['uct2-es-door.mwt2.org', 'uct2-es-head.mwt2.org']
VERSION = '0.1'


def get_mongo_client():
    """
    Function to instantiate a mongodb client that is using the
    condor_history collection

    :return: mongoDB client instance using the condor_history collection
    """
    db_client = pymongo.MongoClient(host=MONGO_SERVER, port=MONGO_SERVER_PORT)
    db = db_client.condor_history
    return db


def get_es_client():
    """
    Function to instantiate an ES client and return object reference for
    further use

    :return: Elasticsearch client instance
    """
    return elasticsearch.Elasticsearch(hosts=ES_NODES,
                                       retry_on_timeout=True,
                                       max_retries=10,
                                       timeout=300)


def get_month_records(year=2014, month=None, db=None):
    """
    Get the condor history records for given year and month from
    mongodb and return a list of records

    :param year: year of interest (as an integer)
    :param month: integer giving the month of interest
    :param db: connection to mongodb
    :return: a list of classads stored as a dictionary
    """
    classads = []
    if month is None or db is None:
        return classads
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year + (month/12), (month % 12) + 1, 1)
    db_query = {"CompletionDate": {"$gte": time.mktime(start_date.timetuple()),
                                   "$lt": time.mktime(end_date.timetuple())}}
    for classad in db.history_records.find(db_query):
        classads.append(classad)
    return classads


def export_to_es(classads, year, month, es_client):
    """
    export classads to appropriate index in elasticsearch
    :param classads: list of classads stored as dicts (e.g. [{}. {}])
    :param year: year that the classads were obtained from
    :param month: year that the classads were obtained from
    :param es_client: Elasticsearch client instance
    :return: nothing
    """
    if not classads:
        return
    actions = []
    index = "osg-connect-job-history-{0}-{1:0>2}".format(year, month)
    timezone = pytz.timezone('US/Central')
    for classad in classads:
        classad_insert = {"_opt_type": "index",
                          "_index": index,
                          "_type": "history-record"}
        classad_insert.update(classad) 
        if 'CompletionDate' in classad_insert:
            timestamp = datetime.datetime.fromtimestamp(classad_insert['CompletionDate'])
            timestamp = timezone.localize(timestamp)
        else:
            timestamp = datetime.datetime(year, month, 1, 0, 0, 0, tzinfo=pytz.utc)
        classad_insert['@timestamp'] = timestamp.isoformat()
        actions.append(classad_insert)
    results = elasticsearch.helpers.bulk(es_client, actions)
    sys.stdout.write("Number of documents indexed: {0}\n".format(results[0]))
    if results[1]:
        sys.stderr.write("Errors encountered:")
        for err in results[1]:
            sys.stderr.write("{0}\n".format(err))


def run_main():
    """
    Main function, parse arguments and then transfer records from mongodb to ES
    """
    parser = argparse.ArgumentParser(description='Insert condor job history from mongodb to ES')
    parser.add_argument('--year', default=0, type=int,
                        help='String indicating year')
    parser.add_argument('--month', default=0, type=int,
                        help='String indicating month')

    parser.add_argument('--version', action='version', version=VERSION)
    args = parser.parse_args()
    if not args.year or not args.month:
        sys.stderr.write("Date must be given\n")
        sys.exit(1)

    mongodb_client = get_mongo_client()
    es_client = get_es_client()
    classads = get_month_records(args.year, args.month, mongodb_client)
    export_to_es(classads, args.year, args.month, es_client)


if __name__ == '__main__':
    run_main()
