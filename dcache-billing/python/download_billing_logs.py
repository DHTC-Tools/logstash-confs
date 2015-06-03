#!/usr/bin/env python

import sys
import urllib2
import argparse

FAXBOX_PROCESSED_CSV_URL = "http://login.usatlas.org/logs/mwt2/dcache-billing/processed/"
FAXBOX_RAW_CSV_URL = "http://login.usatlas.org/logs/mwt2/dcache-billing/raw/"


def download_log(date_string):
    """
    Download job log files from Amazon EC2 machines

    parameters:
    date_string - date to start download
    """
    file_urls = []
    url_file = "billing-{0}".format(date_string)
    file_url = "{0}/{1}/{2}".format(FAXBOX_PROCESSED_CSV_URL,
                                    date_string[0:4],
                                    url_file)
    file_urls.append((url_file, file_url))
    url_file = "billing-error-{0}".format(date_string)
    file_url = "{0}/{1}/{2}".format(FAXBOX_PROCESSED_CSV_URL,
                                    date_string[0:4],
                                    url_file)
    file_urls.append((url_file, file_url))
    for file_info in file_urls:
        try:
            url = file_info[1]
            request = urllib2.urlopen(url)
            if request.getcode() != 200:
                sys.stderr.write("Can't download {0}".format(url))
                return None
        except urllib2.HTTPError:
            sys.stderr.write("Can't download {0}".format(url))
            return False
        output_file = open(file_info[0], 'w')
        for line in request:
            output_file.write(line)
        output_file.close()
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download DCache billing records')
    parser.add_argument('--date', dest='date', default=None, required=True,
                        help='Date to download')

    args = parser.parse_args(sys.argv[1:])
    if len(args.date) != 10:
        sys.stderr.write("Invalid date argument: {0}\n".format(args.date))
    try:
        int(args.date)
    except ValueError:
        sys.stderr.write("Invalid date argument: {0}\n".format(args.date))

    download_log(args.date)
