#!/bin/bash
yesterday=`date --date="yesterday" +"%Y%m%d"`
year=`date --date="yesterday" +"%Y"`
install_dir=$1
orig_dir=`pwd`
cd $install_dir
./generate_ingest_job.py --startdate $yesterday --enddate $yesterday --location /tmp/ingest_billing_logs
cd /tmp/ingest_billing_logs
condor_submit *.submit
condor_wait billing_logs/*.log
cd $orig_dir
rm -fr /tmp/ingest_billing_logs
