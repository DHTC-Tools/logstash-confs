#!/bin/bash

export PATH=/bin:/usr/bin
cur_dir=`pwd`
./process_logs.py
sed -i "s/ES_INDEX/$2/" joblog.conf
sed -i "s/CUR_DIR/$cur_dir/g" joblog.conf
/opt/logstash/bin/logstash -f joblog.conf
