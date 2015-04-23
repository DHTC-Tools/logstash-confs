#!/bin/bash
year=`date --date="3 days ago" +"%Y"`
month=`date --date="3 days ago" +"%m"`
day=`date --date="3 days ago" +"%d"`
isoweek=`python -c "import datetime; print datetime.date($year, $month, $day).isocalendar()[1]"`
index="jobsarchived_"$year"_$isoweek"
curl -m 1800 -XPOST "http://uct2-es-door.mwt2.org:9200/$index/_optimize?max_num_segments=1"
echo "Optimized $index"