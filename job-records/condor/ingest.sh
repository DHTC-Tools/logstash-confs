#!/bin/bash

export PATH=/bin:/usr/bin
cur_dir=`pwd`
if [ "$3" != "True" ];
then
    ./download_logs.py --date $1 --source $2
    ./process_logs.py --date $1
else
    ./download_logs.py --date $1 --source $2 --processed
fi
sed -i "s/ES_INDEX/$4/" joblog.conf
cat *-processed.csv | /opt/logstash/bin/logstash -f joblog.conf
rm *.csv
# need to delete joblog.conf to prevent modified version from being transferred back
rm joblog.conf
sleep 120