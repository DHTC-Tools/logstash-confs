#!/bin/bash

export PATH=/bin:/usr/bin
cur_dir=`pwd`
# save the first three arguments and then discard
source=$1
es_index=$2
processed=$3
shift
shift
shift
while [ "$1" != "" ]; do
    if [ "$processed" == 'True' ];
    then
        ./download_logs.py --date $1 --source $source --processed
    else
        ./download_logs.py --date $1 --source $source
        ./process_logs.py --date $1

    fi
done

sed -i "s/ES_INDEX/$3/" joblog.conf
cat *-processed.csv | /opt/logstash/bin/logstash -f joblog.conf
rm *.csv
