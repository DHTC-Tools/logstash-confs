#!/usr/bin/env python

import sys
import argparse
import re


QUOTE_RE = re.compile(r'.*"[^,]*$')
def continue_line(line):
    """

    :param line: line to examine to see if record continues to next
                 line
    :return: True if record is continued, False if the record is complete
    """
    if QUOTE_RE.match(line):
        # if the line ends with an unclosed quote, it's continued
        return True
    elif (line.count('"') % 2) == 1:
        # if the line doesn't have matched quotes, it's continued
        return True
    elif len(line) > 2048:
        # if the line is more than 2k in length, just close it and
        # move to the next line
        return False
    else:
        return False

def generate_log_lines(input_file, bad_file):
    """
    Generator that processes csv with ATLAS records and try to fix broken lines
    returns fixed lines

    :param input_file: file object with input
    :param badfile: file object to write lines with errors to
    :return: corrected lines stripped of tabs and embedded newlines
    """
    buffer = ""
    for line in input_file:
        buffer += line
        if continue_line(buffer):
            buffer = buffer.replace("\n", " ")
            continue
        else:
            record = buffer
            buffer = ""
            yield record



def process_records(date_string):
    """
    Process log files and remove tabs and try to join broken lines

    parameters:
    date_string - date to start download
    """
    input_file = open("jobsarchived{0}.csv".format(date_string), 'r')
    output_file = open("jobsarchived{0}-processed.csv".format(date_string), 'w')
    bad_file = open("jobsarchived{0}-bad.csv".format(date_string), 'w')

    for line in generate_log_lines(input_file, bad_file):
        output_file.write(line)
    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process ATLAS job records')
    parser.add_argument('--date', dest='date', default=None, required=True,
                        help='Date to process')

    args = parser.parse_args(sys.argv[1:])
    if len(args.date) != 8:
        sys.stderr.write("Invalid date argument: {0}\n".format(args.date))

    try:
        int(args.date)
    except ValueError:
        sys.stderr.write("Invalid date argument: {0}\n".format(args.date))

    process_records(args.date)
