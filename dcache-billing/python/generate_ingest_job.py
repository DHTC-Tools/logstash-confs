#!/usr/bin/env python

import sys
import datetime
import os
import argparse
import tempfile
import shutil
import getpass


ANCILLARY_FILES = ['download_billing_logs.py',
                   '../condor/ingest_dcache_weekly.sh',
                   '../logstash/dcache-billing-full.conf']
ANCILLARY_DIR = ['../logstash/patterns']
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

def create_weekly_submission(start_date, end_date, work_directory):
    """
    Create a condor submit file and ancillary files needed to
    process logs (submits a job per week)

    parameters:
    start_date - beginning date to start downloading from
    end_date   - last date to download job data for
    work_directory  - directory to download files to
    """
    submission_file = open(CONDOR_SUBMIT_TEMPLATE, 'r').read()
    submission_file = submission_file.replace('USER', getpass.getuser())
    submission_file = submission_file.replace('EXECUTABLE', 'ingest_dcache_weekly.sh')
    current_date = start_date
    date_string = current_date.isoformat().replace('-', '')
    current_week = current_date.isocalendar()[1]
    while current_date <= end_date:
        current_date += datetime.timedelta(days=1)
        week = current_date.isocalendar()[1]
        if week != current_week:
            es_index = "billing_{0}_{1:0>2}".format(current_date.year,
                                                    current_week)
            submit_addition = "arguments = {0} {1}\n".format(es_index,
                                                             date_string)
            input_list = [os.path.basename(x) for x in ANCILLARY_FILES + ANCILLARY_DIR]
            transfer_files = ",".join(input_list)
            submit_addition += "transfer_input_files = {0}\n".format(transfer_files)
            submit_addition += "queue 1\n"
            submission_file += submit_addition
            date_string = ""
            current_week = week
        date_string += " {0}".format(current_date.isoformat().replace('-', ''))
        if current_date > end_date:
            # need to write out arguments for this submit now
            es_index = "billing_{0}_{1:0>2}".format(current_date.year,
                                                    current_week)
            submit_addition = "arguments = {0} {1}\n".format(es_index,
                                                             date_string)
            input_list = [os.path.basename(x) for x in ANCILLARY_FILES + ANCILLARY_DIR]
            transfer_files = ",".join(input_list)
            submit_addition += "transfer_input_files = {0}\n".format(transfer_files)
            submit_addition += "queue 1\n"
            submission_file += submit_addition

    output_filename = "ingest_logs_{0}_{1}.submit".format(start_date.isoformat(),
                                                          end_date.isoformat())
    submit_file = open(os.path.join(work_directory, output_filename), 'w')
    submit_file.write(submission_file)
    submit_file.close()
    for filename in ANCILLARY_FILES:
        dst_file = os.path.basename(filename)
        shutil.copyfile(filename, os.path.join(work_directory, dst_file))
    for directory in ANCILLARY_DIR:
        dir_name = os.path.basename(directory)
        shutil.copytree(directory, os.path.join(work_directory, dir_name))
    os.mkdir(os.path.join(work_directory, "billing_logs"))
    os.chmod(os.path.join(work_directory, "download_billing_logs.py"), 0o755)
    os.chmod(os.path.join(work_directory, "ingest_dcache_weekly.sh"), 0o755)


def main():
    """
    Handle argument parsing and dispatch to appropriate functions
    """
    parser = argparse.ArgumentParser(description='Create a condor submit file '
                                                 'for processing job log data.')
    parser.add_argument('--location', dest='location', default=None,
                        help='Location of directory to place submit files')
    parser.add_argument('--startdate', dest='start_date', default=None,
                        help='Date to start processing logs')
    parser.add_argument('--enddate', dest='end_date', default=None,
                        help='Date to stop processing logs')
    parser.add_argument('--force', dest='force', default=False,
                        action='store_true',
                        help='Date to stop processing logs')

    args = parser.parse_args(sys.argv[1:])
    if args.location is None:
        args.location = tempfile.mkdtemp()
    elif not os.path.exists(args.location):
        os.mkdir(args.location, 0o700)
    elif os.path.exists(args.location):
        if not args.force:
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
    create_weekly_submission(start_date, end_date, args.location)

    sys.stdout.write("Submission set up at {0}\n".format(args.location))
    sys.exit(0)

if __name__ == '__main__':
    main()
