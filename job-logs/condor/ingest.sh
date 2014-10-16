#!/bin/bash

export PATH=/bin:/usr/bin
cur_dir=`pwd`
./process_logs.py --date $1
sed -i "s/ES_INDEX/$2/" joblog.conf
cat jobsarchived$1.csv | /opt/logstash/bin/logstash -f joblog.conf
