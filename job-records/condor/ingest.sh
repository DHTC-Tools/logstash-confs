#!/bin/bash

export PATH=/bin:/usr/bin
cur_dir=`pwd`
./download_logs.py --date $1 --source $2
./process_logs.py --date $1 --save-raw
sed -i "s/ES_INDEX/$3/" joblog.conf
cat jobsarchived$1-processed.csv | /opt/logstash/bin/logstash -f joblog.conf
rm *.csv
