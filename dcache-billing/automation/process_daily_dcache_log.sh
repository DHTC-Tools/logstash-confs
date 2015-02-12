#!/bin/bash
yesterday=`date --date="yesterday" +"%Y.%m.%d"`
year=`date --date="yesterday" +"%Y"`
month=`date --date="yesterday" +"%m"`
billing_logs="/var/lib/dcache/billing/$year/$month"
scp uct2-dc4.mwt2.org:$billing_logs/billing-$yesterday /
rm -fr /tmp/faxbox_logs
