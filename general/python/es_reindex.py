#!/usr/bin/env python


# Copyright 2015 University of Chicago
# Available under Apache 2.0 License

import argparse
import sys
import logging

import elasticsearch
import elasticsearch.helpers


ES_NODES = 'uct2-es-door.mwt2.org'
VERSION = '0.1'

def get_es_client(nodes):
    """ Instantiate DB client and pass connection back """
    return elasticsearch.Elasticsearch(hosts=nodes,
                                       retry_on_timeout=True,
                                       max_retries=10,
                                       timeout=300)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reindex events from ' +
                                                 'between ES indices ')
    parser.add_argument('--source', dest='source', default=None,
                        help='name of source index')
    parser.add_argument('--target', dest='target', default=None,
                        help='name of target index')
    parser.add_argument('--server', dest='server', default=ES_NODES,
                        help='hostname for ES server')
    args = parser.parse_args(sys.argv[1:])
    if not args.source or not args.target:
        sys.stderr.write("Need to provide a source and target index\n")
        sys.exit(1)
    client = get_es_client(args.server)
    results = elasticsearch.helpers.reindex(client,
                                            args.source,
                                            args.target,
                                            scroll='30m')
    sys.stdout.write(str(results))