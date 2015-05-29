#!/usr/bin/env python

import argparse
import sys
import logging

import elasticsearch
import elasticsearch.helpers


ES_NODES = 'uct2-es-door.mwt2.org'
VERSION = '0.1'
SOURCE_INDEX = '.kibana'
TARGET_INDEX = 'osg-connect-kibana'

def get_es_client():
    """ Instantiate DB client and pass connection back """
    return elasticsearch.Elasticsearch(hosts=ES_NODES,
                                       retry_on_timeout=True,
                                       max_retries=10,
                                       timeout=300)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reindex events from ' +
                                                 '.kibana ' +
                                                 'to osg-connect-kibana')
    args = parser.parse_args(sys.argv[1:])
    client = get_es_client()
    results = elasticsearch.helpers.reindex(client,
                                            SOURCE_INDEX,
                                            TARGET_INDEX,
                                            scroll='30m')
    sys.stdout.write(str(results))


