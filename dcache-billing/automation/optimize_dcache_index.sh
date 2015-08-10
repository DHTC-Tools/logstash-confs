#!/bin/bash
year=`date --date="yesterday" +"%Y"`
month=`date --date="yesterday" +"%-m"`
day=`date --date="yesterday" +"%-d"`
isoweek=`python -c "import datetime; print datetime.date($year, $month, $day).isocalendar()[1]"`
index="billing_"$year"_$isoweek"
curl -m 1800 -XPOST "http://uct2-es-door.mwt2.org:9200/$index/_optimize?max_num_segments=1"
echo "Optimized $index"
