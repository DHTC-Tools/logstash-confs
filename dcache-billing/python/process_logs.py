#!/usr/bin/env python
"""
Read dcache log files from ./logs directory and write out processed logs to ./processed_logs directory, expects
year for logs as first
"""

import os
import re
import datetime
import pytz

TZ_NAME = 'US/Central'

# looking for billing-YYYY.MM.DD
date_re = re.compile(r'billing-(?:error-)?(\d{4}.\d{2}.\d{2})')
# looking for MM.DD HH:MM:SS ...   the rest of the line is variable depending on message type
billing_re = re.compile(r'\d{2}.\d{2}\s+(\d{2}:\d{2}:\d{2})\s+(.*)')
timezone = pytz.timezone(TZ_NAME)
for logfile in os.listdir('./logs'):
    output = open('./processed_logs/{0}'.format(logfile), 'w')
    date_match = date_re.match(logfile)
    if not date_match:
        print "Can't match {0}".format(logfile)
        continue
    date = date_match.group(1).split('.')
    previous_line = ""
    # counter used to figure out if line needs to continue.  Essentially
    # add 1 for each [ or { and subtract one for each ] or } 
    # if count is non-zero continue line
    balance_count = 0
    for line in open("./logs/" + logfile,'r'):
        balance_count += line.count("[") + line.count("{")
        balance_count -= line.count("]") + line.count("}")
        if balance_count != 0:
            # line got continued
            previous_line = previous_line.strip() + line.strip()
            continue
        else:
            if previous_line != "":
                line = previous_line.strip() + line.strip()
                balance_count = 0
                previous_line = ""
        field_match = billing_re.search(line)
        if field_match is None:
            print "Can't match {0}".format(line)
            continue
        time = field_match.group(1).split(':')
        # datetime(year, month, day, hour, minute, sec)
        timestamp = timezone.localize(datetime.datetime(int(date[0]),
                                                        int(date[1]),
                                                        int(date[2]),
                                                        int(time[0]),
                                                        int(time[1]),
                                                        int(time[2])))
        output.write("{0} {1}\n".format(timestamp.isoformat(),
                                        field_match.group(2)))
