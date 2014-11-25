#!/usr/bin/env python

import sys
import urllib2
import argparse

AMAZON_CSV_URL = "http://atlas-panda-jobsarchived.s3.amazonaws.com"
FAXBOX_PROCESSED_CSV_URL = "http://faxbox.usatlas.org/group/logs/jobs/processed/"
FAXBOX_RAW_CSV_URL = "http://faxbox.usatlas.org/group/logs/jobs/raw/"

def download_log(date_string, source=None, processed=False):
    """
    Download job log files from Amazon EC2 machines

    parameters:
    date_string - date to start download
    source      - string set to either faxbox or amazon to indicate where
                  to get logs from
    """
    if source is None:
        return False
    elif source.lower() == 'amazon':
        url_file = "jobsarchived{0}.csv".format(date_string)
        csv_url = "{0}/{1}".format(AMAZON_CSV_URL, url_file)
    elif source.lower() == 'faxbox':
        if processed:
            url_file = "jobsarchived{0}-processed.csv".format(date_string)
            csv_url = "{0}/{1}/{2}".format(FAXBOX_PROCESSED_CSV_URL,
                                           date_string[0:4],
                                           url_file)
        else:
            url_file = "jobsarchived{0}.csv".format(date_string)
            csv_url = "{0}/{1}/{2}".format(FAXBOX_RAW_CSV_URL,
                                           date_string[0:4],
                                           url_file)
    else:
        return False
    try:
        request = urllib2.urlopen(csv_url)
        if request.getcode() != 200:
            sys.stderr.write("Can't download {0}".format(csv_url))
            return None
    except urllib2.HTTPError:
        sys.stderr.write("Can't download {0}".format(csv_url))
        return False
    output_file = open(url_file, 'w')
    for line in request:
        output_file.write(line)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download ATLAS job records')
    parser.add_argument('--date', dest='date', default=None, required=True,
                        help='Date to download')
    parser.add_argument('--source', dest='source', default=None,
                        choices=['amazon', 'faxbox'], required=True,
                        help='filename of input file')
    parser.add_argument('--processed', dest='processed',
                        action='store_true',
                        help='Download processed logs (faxbox only)')

    args = parser.parse_args(sys.argv[1:])
    if len(args.date) != 8:
        sys.stderr.write("Invalid date argument: {0}\n".format(args.date))
    try:
        int(args.date)
    except ValueError:
        sys.stderr.write("Invalid date argument: {0}\n".format(args.date))

    download_log(args.date, args.source, args.processed)
