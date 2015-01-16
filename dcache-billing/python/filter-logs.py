#!/usr/bin/env python
"""
Read dcache log files from stdin and write out processed logs files, needs the year for the log files as the first
argument
"""

import sys
import os
import re
import datetime
import pytz

TZ_NAME = 'US/Central'

date_re = re.compile(r'summary-(\d{4}.\d{2}.\d{2})')
billing_re = re.compile(r'(\d{2}.\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(.*)\s+(\d+)\s+((?:-)?\d+)\s+(\d+)')
timezone = pytz.timezone(TZ_NAME)
utc_tz = pytz.timezone('UTC')
year = sys.argv[1]
for line in sys.stdin.readlines():
    field_match = billing_re.search(line)
    if field_match is None:
        print "Can't match {0}".format(line)
        continue
    date = field_match.group(1).split('.')
    time = field_match.group(2).split(':')
    # datetime(year, month, day, hour, minute, sec)
    timestamp = timezone.localize(datetime.datetime(int(year),
                                                    int(date[0]),
                                                    int(date[1]),
                                                    int(time[0]),
                                                    int(time[1]),
                                                    int(time[2])))
    sys.stdout.write("{0} {1} {2} {3} {4}\n".format(timestamp.astimezone(utc_tz).isoformat(),
                                                    field_match.group(3),
                                                    field_match.group(4),
                                                    field_match.group(5),
                                                    field_match.group(6)))
