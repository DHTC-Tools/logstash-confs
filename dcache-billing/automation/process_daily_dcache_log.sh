#!/bin/bash
yesterday=`date --date="yesterday" +"%Y.%m.%d"`
year=`date --date="yesterday" +"%Y"`
month=`date --date="yesterday" +"%m"`
billing_logs="/var/lib/dcache/billing/$year/$month"
log_dest="/mnt/logs/mwt2/dcache-billing/"
work_dir=`mktemp -d`
cd $work_dir
mkdir logs
mkdir processed_logs
scp uct2-dc4.mwt2.org:$billing_logs/billing-$yesterday logs/
scp uct2-dc4.mwt2.org:$billing_logs/billing-error-$yesterday logs/
$1/python/process_logs.py
cd logs
sha256sum billing* > raw_sums
cd ../processed_logs
sha256sum billing* > processed_sums
cd ..
cp logs/billing* $log_dest/raw/$year
cp processed_logs/billing* $log_dest/processed/$year
cat logs/raw_sums >> $log_dest/raw/$year/sha256sums
cat processed_logs/processed_sums >> $log_dest/processed/$year/sha256sums
rm -fr $work_dir
