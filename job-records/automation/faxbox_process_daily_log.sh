#!/bin/bash
yesterday=`date --date="3 days ago" +"%Y%m%d"`
year=`date --date="3 days ago" +"%Y"`
faxbox_logs="/faxbox/group/logs/jobs"
curr_dir=`pwd`
cd $1
./generate_process_submit.py --startdate $yesterday --enddate $yesterday --location /tmp/faxbox_logs --data_source amazon
cd /tmp/faxbox_logs
submit_file=`ls *.submit`
sed 's/.*queue 1.*/+Project="atlas-org-uchicago"\n&/' $submit_file  > temp_file
sed 's/.*queue 1.*/Requirements = regexp("uc3-c.*", Machine)\n&/' temp_file > $submit_file
condor_submit *.submit
condor_wait job_logs/*.log
mv jobsarchived$yesterday-processed.csv  $faxbox_logs/processed/$year
mv jobsarchived$yesterday-bad.csv  $faxbox_logs/processed/$year
mv jobsarchived$yesterday.csv  $faxbox_logs/raw/$year
rm -fr /tmp/faxbox_logs
cd $curr_dir
