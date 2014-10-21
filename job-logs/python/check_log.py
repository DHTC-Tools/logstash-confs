import sys
import argparse
import csv


def examine_log(filename, save_raw=False):
    """
    Download job log files from Amazon EC2 machines

    parameters:
    filename - beginning date to start downloading from
    work_directory  - directory to download files to
    """
    input_file =- open(filename, 'r')
    csv_input = csv.reader(input_file)
    error = 0
    for row in csv_input:
        if len(row) != 87:
            error += 1
    print error
    sys.stderr.write("{0} lines skipped due to errors".format(error_lines))
    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process ATLAS job records')
    parser.add_argument('--filename', dest='filename', default=None,
                        help='filename of input file')
    parser.add_argument('--save-raw', dest='save_raw',
                        action='store_true',
                        help='Save raw log files instead of replacing in place')

    args = parser.parse_args(sys.argv[1:])
    examine_log(args.filename, args.save_raw)