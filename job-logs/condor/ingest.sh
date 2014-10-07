#!/bin/bash

./process_logs.py
sed -i "s/ES_INDEX/$2/" joblog.conf
 /opt/logstash/bin/logstash -f joblog.conf
