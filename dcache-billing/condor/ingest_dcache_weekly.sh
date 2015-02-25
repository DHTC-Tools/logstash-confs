#!/bin/bash

export PATH=/bin:/usr/bin
cur_dir=`pwd`
# save the first three arguments and then discard
es_index=$1
shift
shift
shift
sed -i "s/DCACHE_INDEX/$es_index/" joblog.conf
while [ "$1" != "" ]; do
    ./download_billing_logs.py --date $1
    cat billing-$1 | /opt/logstash/bin/logstash -f dcache-billing-full.conf
    cat billing-error-$1 | /opt/logstash/bin/logstash -f dcache-billing-full.conf
    sleep 120
    shift
done

rm billing*
# need to delete joblog.conf to prevent modified version from being transferred back
rm dcache-billing-full.conf
