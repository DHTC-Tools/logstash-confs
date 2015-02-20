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
sed -i "s/ES_INDEX/$es_index/" joblog.conf
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
# need to delete joblog.conf to prevent modified version from being transferred back
rm joblog.conf
