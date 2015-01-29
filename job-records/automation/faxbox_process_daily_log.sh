#!/bin/bash
yesterday=`date --date="3 days ago" +"%Y%m%d"`
year=`date --date="3 days ago" +"%Y"`
faxbox_logs="/faxbox/group/logs/panda_logs/$year/"
./generate_process_submit.py --startdate $yesterday --enddate $yesterday --location /tmp/faxbox_logs
cd /tmp/faxbox_logs
condor_submit *.submit
mv jobsarchived$yesterday-processed.log  $faxbog_logs/processed
mv jobsarchived$yesterday-error.log  $faxbog_logs/processed
mv jobsarchived$yesterday.log  $faxbog_logs/raw
cd
rm -fr /tmp/faxbox_logs
