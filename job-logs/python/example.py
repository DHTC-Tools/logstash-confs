#!/usr/bin/env python

from pyelasticsearch import ElasticSearch
es = ElasticSearch('http://uct2-es1.mwt2.org:9200/')

query = {
  "query": {
    "query_string": {
      "default_field": "atlas_release",
      "query": "Atlas-17.2.7"
    }
  },
  "script_fields": {
    "test_duration": {
      "script": "doc['end_time'].value - doc['start_time'].value",
      "lang": "groovy",
      "params": {}
    }
  }
} 

count = 0
sum = 0
results = es.search(query, index='pilot_logs')
for result in results['hits']['hits']: 
    sum += result['fields']['test_duration'][0] / 1000
    count += 1
print "Average duration: {0}".format(float(sum)/count)
