#!/usr/bin/env python

# Copyright 2015 University of Chicago

import sys
import argparse
import logging
import pytz
import os
import pwd
import grp
import datetime

import elasticsearch
import elasticsearch.helpers


ES_NODES = ['uct2-es-head.mwt2.org:9200', 'uct2-es-door.mwt2.org:9200']
TZ_NAME = "US/Central"
TIMEZONE = pytz.timezone(TZ_NAME)


def get_es_client():
    """ Instantiate DB client and pass connection back """
    return elasticsearch.Elasticsearch(hosts=ES_NODES,
                                       retry_on_timeout=True,
                                       max_retries=10,
                                       timeout=300)


def create_record(dirpath, num_files, date, dir_size=None,
                  index=None, ceph_fs=False):
    """
    Query directory at dirpath for information and store information in ES

    :param dirpath: string storing path to file
    :parm num_files: number of files present in dirpath
    :param date: datetime.date with date to use
    :param dir_size: size of directory and contents in bytes
    :param index: ES index for records
    :param ceph_fs: Is the directory on a CephFS filesystem
    :return: dictionary with record if successful, empty dict otherwise
    """
    if not os.path.isdir(dirpath):
        return {}
    if not index:
        index = "stash-space-{0}-{1:0>2}".format(date.year, date.month)
    dir_info = os.stat(dirpath)
    uid = dir_info.st_uid
    gid = dir_info.st_gid
    ctime = datetime.datetime.fromtimestamp(dir_info.st_ctime, TIMEZONE)
    mtime = datetime.datetime.fromtimestamp(dir_info.st_mtime, TIMEZONE)
    record_fields = {'@timestamp': date.isoformat(),
                     'size': dir_size,
                     'num_files': num_files,
                     'ctime': ctime,
                     'mtime': mtime,
                     'user': pwd.getpwuid(uid).pw_name,
                     'group': grp.getgrgid(gid).gr_name,
                     'path': dirpath}
    record = {'_index': index,
              '_source': record_fields,
              '_op_type': 'index',
              '_type': 'space_usage_record'}
    return record


def get_ceph_dir_size(root):
    """
    Get the space used by a directory and it's contents on a CephFS
    :param root: path to directory
    :return: number of bytes used by the directory and it's contents
    """
    return os.stat(root, follow_symlinks=False).st_size

def get_dir_size(root, dir_sizes, inodes):
    """
    Get the size of a directory and it's contents

    :param root: path to the directory
    :param dir_sizes: a dictionary of directories with sizes of those
                      directories
    :param inodes: a set with list of inodes that have been visited
    :return: number of bytes used by the directory and it's contents
    """

    total_size = 0
    entries = os.listdir(root)
    for entry in entries:
        entry_name = os.path.join(root, entry)
        inode = os.stat(entry_name).st_ino
        if inode in inodes:
            continue
        if os.path.isfile(entry_name) and not os.path.islink(entry_name):
            try:
                total_size += os.stat(entry_name).st_size
                inodes.add(inode)
            except OSError:
                continue
        elif os.path.isdir(entry_name) and not os.path.islink(entry_name):
            if entry_name in dir_sizes:
                total_size += dir_sizes[entry_name]
                continue
            dir_size = get_dir_size(entry_name, dir_sizes, inodes)
            dir_sizes[entry_name] = dir_size
            inodes.add(inode)
    return total_size


def traverse_directory(dirpath, index=None, ceph_fs=False):
    """
    Traverse subdirectories and create a set of records
    with space usage
    :param dirpath: path to directory to
    :param index: the ES index to store records in
    :param ceph_fs: Whether the dirpath is a CephFS directory
    :return: Nothing
    """
    current_date = TIMEZONE.localize(datetime.datetime.combine(datetime.date.today(),
                                                               datetime.time(0, 0, 0)))

    if not os.path.isdir(dirpath):
        return
    records = []
    if ceph_fs:
        topdown = True
    else:
        topdown = False
        dir_sizes = {}
    for root, dirs, files in os.walk(dirpath, topdown=topdown):
        if not ceph_fs:
            inodes = set()
            size = get_dir_size(root, dir_sizes, inodes)
        else:
            size = get_ceph_dir_size(root)
        record = create_record(root, len(files), current_date, size,
                               index, ceph_fs)
        if record:
            records.append(record)
    save_records(records)

def save_records(records=None):
    """
    Save a job record to ES
    """
    es_client = get_es_client()
    elasticsearch.helpers.bulk(es_client,
                               records,
                               stats_only=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get space usage on a given '
                                                 'filesystem and store in ES')
    parser.add_argument('--index', dest='index', default=None,
                        help='ES index to store records in')
    parser.add_argument('--is-ceph', dest='ceph_fs', default=False,
                        type=bool, action='store_true',
                        help='Is the directory a CephFS directory?')
    parser.add_argument("directory", default=None,
                        help="Directory to examine")
    args = parser.parse_args(sys.argv[1:])
    if not os.path.isdir(args.directory):
        sys.stderr.write("{0} must be a directory\n".format(args.directory))
        sys.exit(1)
    traverse_directory(args.directory, args.index, args.ceph_fs)
