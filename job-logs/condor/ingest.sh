#!/bin/bash

export PATH=/bin:/usr/bin
cur_dir=`pwd`
./process_logs.py $1
sed -i "s/ES_INDEX/$2/" joblog.conf
sed -i "s/DATESTRING/$1/" joblog.conf
sed -i "s|CUR_DIR|$cur_dir|" joblog.conf
/opt/logstash/bin/logstash -f joblog.conf
