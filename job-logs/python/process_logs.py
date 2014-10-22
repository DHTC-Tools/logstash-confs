#!/usr/bin/env python

import sys
import urllib2
import argparse

JOB_LOG_URL = "http://atlas-panda-jobsarchived.s3.amazonaws.com"


def download_log(date_string, filename=None, save_raw=False):
    """
    Download job log files from Amazon EC2 machines

    parameters:
    date_string - date to start download
    filename    - filename of already downloaded csv file, specifying this
                  results in this file being used instead of a download
    save_raw    - preserve original files?
    """
    if filename is None:
        url_file = "jobsarchived{0}.csv".format(date_string)
        if save_raw:
            csv_file = "jobsarchived{0}-cleaned.csv".format(date_string)
        else:
            csv_file = "jobsarchived{0}.csv".format(date_string)
        csv_url = "{0}/{1}".format(JOB_LOG_URL, url_file)
        try:
            request = urllib2.urlopen(csv_url)
            if request.getcode() != 200:
                sys.stderr.write("Can't download {0}".format(csv_url))
                return None
        except urllib2.HTTPError:
            sys.stderr.write("Can't download {0}".format(csv_url))
            return None
        if save_raw:
            orig_file = open(url_file, 'w')
    else:
        request = open(filename, 'r')
        if save_raw:
            csv_file = "{0}-cleaned.csv".format(filename)
        else:
            csv_file = "{0}.csv".format(filename)

    output_file = open(csv_file, 'w')
    error_lines = 0
    for line in request:
        if save_raw and filename is None:
            orig_file.write(line)
        line = line.replace("\t", '')
        if len(line.split(',')) != 87:
            error_lines += 1
            continue
        output_file.write(line)
    sys.stderr.write("{0} lines skipped due to errors".format(error_lines))
    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download and process ATLAS'
                                                 'job records')
    parser.add_argument('--date', dest='date', default=None,
                        help='Date to download')
    parser.add_argument('--filename', dest='filename', default=None,
                        help='filename of input file')
    parser.add_argument('--save-raw', dest='save_raw',
                        action='store_true',
                        help='Save raw log files instead of replacing in place')

    args = parser.parse_args(sys.argv[1:])
    if args.filename is not None and len(args.date) != 8:
        sys.stderr.write("Invalid date argument: {0}\n".format(args.date))
    if args.date is not None:
        try:
            int(args.date)
        except ValueError:
            sys.stderr.write("Invalid date argument: {0}\n".format(args.date))

    download_log(args.date, args.filename, args.save_raw)
