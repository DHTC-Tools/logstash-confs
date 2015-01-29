#!/bin/bash
yesterday=`date --date="3 days ago" +"%Y%m%d"`
year=`date --date="3 days ago" +"%Y"`
faxbox_logs="/faxbox/group/logs/panda_logs/$year/"
./generate_ingest_submit.py --startdate $yesterday --enddate $yesterday --location /tmp/ingest_logs
cd /tmp/ingest_logs
condor_submit *.submit
cd
rm -fr /tmp/ingest_logs
