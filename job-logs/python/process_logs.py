#!/usr/bin/env python

import os
import re
import sys


csv_re = re.compile(r'(.*)\.csv')
for logfile in os.listdir('.'):
    if not logfile.endswith('-corrected.csv'):
        continue
    filename = csv_re.match(logfile).group(1)
    output = open('./{0}-corrected.csv'.format(filename), 'w')
    for line in open(logfile, 'r'):
        if len(line.split(',')) != 87:
            sys.stdout.write(line)
        else:
            output.write(line)
