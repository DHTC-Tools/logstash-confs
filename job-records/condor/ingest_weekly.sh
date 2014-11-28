#!/bin/bash

export PATH=/bin:/usr/bin
cur_dir=`pwd`
# save the first three arguments and then discard
source=$1
es_index=$2
processed=$3
sed -i "s/ES_INDEX/$es_index/" joblog.conf
# create index with one replica per index, it's faster although will cause
# problems if data node goes down while indexing
curl -XPUT "http://uct2-es-door.mwt2.org:9200/$es_index" -d '{ "settings" : { "number_of_replicas" : 0 } }'
shift
shift
shift
while [ "$1" != "" ]; do
    if [ "$processed" == 'True' ];
    then
        ./download_logs.py --date $1 --source ${source} --processed
        cat jobsarchived$1-processed.csv | /opt/logstash/bin/logstash -f joblog.conf
        sleep 120
    else
        ./download_logs.py --date $1 --source ${source}
        ./process_logs.py --date $1
        cat jobsarchived$1-processed.csv | /opt/logstash/bin/logstash -f joblog.conf
        sleep 120
    fi
    shift
done

rm *.csv
