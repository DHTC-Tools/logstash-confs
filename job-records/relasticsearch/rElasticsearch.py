#!/usr/bin/env python
import elasticsearch

def getFields(index=None, fields=None):
    """
    Query elasticsearch and get fields requested

    :param index: name of index to query
    :param columns: a list of fields to
    :return: Returns a list with the values for each column
    """

    if index is None:
        return []
    if fields is None:
        return []

    results = []
    for i in range(0, len(fields)):
        results[i] = []
    es = elasticsearch.Elasticsearch(sniff_on_start=True, sniff_on_connection_fail=True, sniffer_timeout=60)
    for document in es.get(index=index, fields=fields):
        col = 0
        for field in fields:
            results[col].append(document[field])

    return results



