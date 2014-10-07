#!/usr/bin/env python

import sys
import datetime
import urllib2
import os
import argparse
import tempfile
import shutil

JOB_LOG_URL = "http://atlas-panda-jobsarchived.s3.amazonaws.com"
CONDOR_SUBMIT_TEMPLATE = "../condor/submit_template"

def validate_date(arg):
    """
    Validate that text string provided is a valid date
    """
    if arg is None or len(arg) != 8:
        return None
    year = arg[0:4]
    month = arg[4:6]
    day = arg[6:8]
    try:
        year = int(year)
        month = int(month)
        day = int(day)
    except ValueError:
        return None
    if year < 2000 or year > 2038:
        return None
    if month < 1 or month > 12:
        return None
    if day < 1 or day > 31:
        return None
    try:
        temp = datetime.date(year, month, day)
    except ValueError:
        return None
    return temp

def download_logs(start_date, end_date, work_directory):
    """
    Download job log files from Amazon EC2 machines

    parameters:
    start_date - beginning date to start downloading from 
    end_date   - last date to dowload job data for
    work_directory  - directory to download files to
    """
    current_date = start_date
    while current_date <= end_date:
        csv_file = "jobsarchived{0}{1:0>2}{2:0>2}.csv".format(current_date.year,
                                                              current_date.month,
                                                              current_date.day)
        csv_url = "{0}/{1}".format(JOB_LOG_URL, csv_file)
        request = urllib2.urlopen(csv_url)
        if request.getcode() != 200:
            sys.stderr.write("Can't download {0}".format(csv_url))
            continue
        fh = open(os.path.join(work_directory, csv_file), 'w')
        shutil.copyfileobj(request, fh)
        fh.close()
        current_date += datetime.timedelta(days=1)

    return None

def create_submission(start_date, end_date, work_directory):
    """
    Create a condor submit file and ancillary files needed to

    parameters:
    start_date - beginning date to start downloading from
    end_date   - last date to dowload job data for
    work_directory  - directory to download files to
    """
    submission_file = open(CONDOR_SUBMIT_TEMPLATE, 'r').read()
    current_date = start_date
    while current_date <= end_date:
        date_string = current_date.isoformat().replace('-', '')
        es_index = "jobsarchived_{0}_{0:0>2}".format(current_date.year,
                                                     current_date.isocalendar()[1])
        submit_addition = "arguments = {0} {1}\n".format(date_string,
                                                         es_index)
        submit_addition += ("transfer_input_files = process_logs.py " +
                            "jobsarchived{0}-processed.csv\n".format(date_string))
        submit_addition += "queue 1\n"
        submission_file += submit_addition
        current_date += datetime.timedelta(days=1)
    output_filename = "process_logs_{0}_{1}.submit".format(start_date.isoformat(),
                                                           end_date.isoformat())
    submit_file = open(os.path.join(work_directory, output_filename), 'w')
    submit_file.write(submission_file)
    submit_file.close()




def main():
    """
    Handle argument parsing and dispatch to appropriate functions
    """
    parser = argparse.ArgumentParser(description='Create a condor submit file for processing job log data.')
    parser.add_argument('--location', dest='location', default=None,
                        help='Location directory to place files in')
    parser.add_argument('--startdate', dest='start_date', default=None,
                        help='Date to start processing logs from')
    parser.add_argument('--enddate', dest='end_date', default=None,
                        help='Date to stop processing logs')
    args = parser.parse_args(sys.argv[1:])
    if args.location is None:
        args.location = tempfile.mkdtemp()
    elif os.path.exists(args.location):
        overwrite = raw_input("{0} exists, overwrite? ".format(args.location))
        if overwrite.lower().strip() != 'y':
            sys.stderr.write("Exiting...")
            sys.exit(0)
        shutil.rmtree(args.location)
        os.mkdir(args.location)
    start_date = validate_date(args.start_date)
    if start_date is None:
        sys.stderr.write("startdate must be in YYYYMMDD format, "
                         "got {0}\n".format(args.start_date))
        sys.exit(1)
    end_date = validate_date(args.end_date)
    if end_date is None:
        sys.stderr.write("enddate must be in YYYYMMDD format, "
                         "got {0}\n".format(args.end_date))
        sys.exit(1)
    download_logs(start_date, end_date, args.location)
    process_logs(start_date, end_date, args.location)
    create_submission(start_date, end_date, args.location)
    sys.stdout.write("Submission set up at {0}\n".format(args.location))



if __name__ == '__main__':
    main()
