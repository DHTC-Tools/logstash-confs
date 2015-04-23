#!/usr/bin/env bash
#!/bin/bash
year=`date --date="yesterday" +"%Y"`
month=`date --date="yesterday" +"%m"`
index="osg-connect-job-history-$year-$month"
curl -m 1800 -XPOST "http://uct2-es-door.mwt2.org:9200/$index/_optimize?max_num_segments=1"
echo "Optimized $index"