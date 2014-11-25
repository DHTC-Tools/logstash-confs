#!/bin/bash

export PATH=/bin:/usr/bin
cur_dir=`pwd`
./download_logs.py --date $1 --source $2
if [ "$2" != "faxbox" ];
then
    ./process_logs.py --date $1
fi
sed -i "s/ES_INDEX/$3/" joblog.conf
cat *-processed.csv | /opt/logstash/bin/logstash -f joblog.conf
rm *.csv
