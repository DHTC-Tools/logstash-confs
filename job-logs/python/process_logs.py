#!/usr/bin/env python

import sys
import urllib2

JOB_LOG_URL = "http://atlas-panda-jobsarchived.s3.amazonaws.com"


def download_log(date_string, save_raw=False):
    """
    Download job log files from Amazon EC2 machines

    parameters:
    start_date - beginning date to start downloading from
    end_date   - last date to dowload job data for
    work_directory  - directory to download files to
    """
    if save_raw:
        csv_file = "jobsarchived{0}-cleaned.csv".format(date_string)
    else:
        csv_file = "jobsarchived{0}.csv".format(date_string)
    csv_url = "{0}/{1}".format(JOB_LOG_URL, csv_file)
    request = urllib2.urlopen(csv_url)
    if request.getcode() != 200:
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
    if len(sys.argv) != 2:
        sys.stderr.write("Need an argument\n")
        sys.exit(1)
    if len(sys.argv[1]) != 8:
        sys.stderr.write("Invalid date argument: {0}\n".format(sys.argv[1]))
    try:
        int(sys.argv[1])
    except ValueError:
        sys.stderr.write("Invalid date argument: {0}\n".format(sys.argv[1]))
    if len(sys.argv) == 3 and sys.argv[2] == 'save':
        save_raw = True
    else:
        save_raw = False

    download_log(sys.argv[1], save_raw=True)
