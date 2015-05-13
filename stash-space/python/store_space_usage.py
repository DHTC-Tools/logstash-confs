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

import xattr
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


def create_record(dirpath, num_files, date, dir_size=None, index=None):
    """
    Query directory at dirpath for information and store information in ES

    :param dirpath: string storing path to file
    :parm num_files: number of files present in dirpath
    :param date: datetime.date with date to use
    :param dir_size: size of directory and contents in bytes
    :param index: ES index for records
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
    try:
        group = grp.getgrgid(gid).gr_name
    except KeyError:
        group = gid
    try:
        user = pwd.getpwuid(uid).pw_name
    except KeyError:
        user = uid
    record_fields = {'@timestamp': date.isoformat(),
                     'size': dir_size,
                     'num_files': num_files,
                     'ctime': ctime.isoformat(),
                     'mtime': mtime.isoformat(),
                     'user': user,
                     'group': group,
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


def get_dir_size(root, inodes):
    """
    Get the size of a directory and it's contents

    :param root: path to the directory
    :param inodes: a set with list of inodes that have been visited
    :return: number of bytes used by the directory and it's contents
    """

    total_size = 0
    entries = os.listdir(root)
    for entry in entries:
        entry_name = os.path.join(root, entry)
        try:
            entry_stat = os.stat(entry_name)
        except OSError:
            continue
        if entry_stat.st_ino in inodes:
            continue
        if os.path.isfile(entry_name) and not os.path.islink(entry_name):
            try:
                total_size += entry_stat.st_size
                inodes.add(entry_stat.st_ino)
            except OSError:
                continue
    total_size += os.stat(root).st_size
    return total_size

def get_top_level_info(dirpath):
    """
    Temporary function to just get top level info on user and project directories
    :param dirpath: path to stash installation
    :return: a list with dictionaries containing user/project information
    """

    directories = []
    if not os.path.isdir(dirpath):
        return directories
    for entry in os.listdir(os.path.join(dirpath, 'user')):
        dir_info = {}
        full_path = os.path.join(dirpath, 'user', entry)
        if not os.path.isdir(full_path):
            continue
        dir_info['name'] = full_path
        dir_info['files'] = int(xattr.getxattr('/stash/user/sthapa',
                                               'ceph.dir.rfiles')[:-1])
        dir_info['size'] = int(xattr.getxattr('/stash/user/sthapa',
                                              'ceph.dir.rbytes')[:-1])
        directories.append(dir_info)
    for entry in os.listdir(os.path.join(dirpath, 'project/')):
        full_path = os.path.join(dirpath, 'project', entry)
        if not os.path.isdir(full_path):
            continue
        dir_info['name'] = full_path
        dir_info['files'] = int(xattr.getxattr('/stash/user/sthapa',
                                               'ceph.dir.rfiles')[:-1])
        dir_info['size'] = int(xattr.getxattr('/stash/user/sthapa',
                                              'ceph.dir.rbytes')[:-1])
        directories.append(dir_info)

    return directories

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
        # for ceph directories just get top-level user and project information
        # for now, this will get removed to get more detailed information on the new
        # Ceph filesystem
        directories = get_top_level_info(dirpath)
        for dir in directories:
            record = create_record(dir['name'],
                                   dir['files'],
                                   current_date,
                                   dir['size'],
                                   index)
            if record:
                records.append(record)
        save_records(records)
        return

    if ceph_fs:
        topdown = True
    else:
        topdown = False
    for root, dirs, files in os.walk(dirpath, topdown=topdown):
        if not ceph_fs:
            inodes = set()
            size = get_dir_size(root, inodes)
        else:
            size = get_ceph_dir_size(root)
        record = create_record(root, len(files), current_date, size, index)
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
                        action='store_true',
                        help='Is the directory a CephFS directory?')
    parser.add_argument("directory", default=None,
                        help="Directory to examine")
    args = parser.parse_args(sys.argv[1:])
    if not os.path.isdir(args.directory):
        sys.stderr.write("{0} must be a directory\n".format(args.directory))
        sys.exit(1)
    traverse_directory(args.directory, args.index, args.ceph_fs)
