#!/bin/bash
yesterday=`date --date="3 days ago" +"%Y%m%d"`
year=`date --date="3 days ago" +"%Y"`
cd $1
./generate_ingest_submit.py --startdate $yesterday --enddate $yesterday --location /tmp/ingest_logs --data_source faxbox
cd /tmp/ingest_logs
condor_submit *.submit
condor_wait job_logs/*.log
cd
rm -fr /tmp/ingest_logs
