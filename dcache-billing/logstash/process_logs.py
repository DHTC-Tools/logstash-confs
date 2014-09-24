#!/usr/bin/env python

import os
import re
import datetime
import pytz

TZ_NAME = 'US/Central'

date_re = re.compile(r'summary-(\d{4}.\d{2}.\d{2})')
billing_re = re.compile(r'\d{2}.\d{2}\s+(\d{2}:\d{2}:\d{2})\s+(.*)\s+(\d+)\s+((?:-)?\d+)\s+(\d+)')
timezone = pytz.timezone(TZ_NAME)
for logfile in os.listdir('./logs'):
    output = open('./processed_logs/{0}'.format(logfile), 'w')
    date_match = date_re.match(logfile)
    if not date_match:
        print "Can't match {0}".format(logfile)
        continue
    date = date_match.group(1).split('.')
    for line in open("./logs/" + logfile,'r'):
        field_match = billing_re.search(line)
        if field_match is None:
            print "Can't match {0}".format(line)
            continue
        time = field_match.group(1).split(':')
        # datetime(year, month, day, hour, minute, sec)
        timestamp =  timezone.localize(datetime.datetime(int(date[0]),
                                                         int(date[1]),
                                                         int(date[2]),
                                                         int(time[0]),
                                                         int(time[1]),
                                                         int(time[2])))
        output.write("{0} {1} {2} {3} {4}\n".format(timestamp.isoformat(),
                                                    field_match.group(2),
                                                    field_match.group(3),
                                                    field_match.group(4),
                                                    field_match.group(5)))
