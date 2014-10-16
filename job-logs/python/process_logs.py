#!/usr/bin/env python

import sys
import urllib2
import argparse

JOB_LOG_URL = "http://atlas-panda-jobsarchived.s3.amazonaws.com"


def download_log(date_string, save_raw=False):
    """
    Download job log files from Amazon EC2 machines

    parameters:
    start_date - beginning date to start downloading from
    end_date   - last date to dowload job data for
    work_directory  - directory to download files to
    """
    url_file = "jobsarchived{0}.csv".format(date_string)
    if save_raw:
        csv_file = "jobsarchived{0}-cleaned.csv".format(date_string)
    else:
        csv_file = "jobsarchived{0}.csv".format(date_string)
    csv_url = "{0}/{1}".format(JOB_LOG_URL, csv_file)
    try:
        request = urllib2.urlopen(csv_url)
        if request.getcode() != 200:
            sys.stderr.write("Can't download {0}".format(csv_url))
            return None
    except urllib2.HTTPError:
        sys.stderr.write("Can't download {0}".format(csv_url))
        return None
    output_file = open(csv_file, 'w')
    error_lines = 0
    for line in request:
        if len(line.split(',')) != 87:
            error_lines += 1
        else:
            output_file.write(line)
    sys.stderr.write("{0} lines skipped due to errors".format(error_lines))
    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download and process ATLAS'
                                                 'job records')
    parser.add_argument('--date', dest='date', default=None,
                        help='Date to download')
    parser.add_argument('--save-raw', dest='save_raw',
                        action='store_true',
                        help='Save raw log files instead of replacing in place')

    args = parser.parse_args(sys.argv[1:])
    if len(args.date) != 8:
        sys.stderr.write("Invalid date argument: {0}\n".format(args.date))
    try:
        int(args.date)
    except ValueError:
        sys.stderr.write("Invalid date argument: {0}\n".format(args.date))

    download_log(args.date, args.save_raw)
