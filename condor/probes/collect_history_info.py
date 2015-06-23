#!/usr/bin/env python

# Copyright 2015 University of Chicago
# Available under Apache 2.0 License

import time
import os
import json
import argparse
import sys
import cPickle

import redis

import probe_libs.history_watcher

VERSION = '0.6'
REDIS_SERVER = 'db.mwt2.org'
REDIS_CHANNEL = 'osg-connect-history'
CONDOR_HISTORY_LOG_DIR = '/var/lib/condor/'
# number of seconds to wait before polling history file
POLL_INTERVAL = 60
STATE_FILE_PATH = '/var/lib/collect_history/state_info'


def publish_classad(classad, channel, redis_client):
    """
    Publishes a classad to a Redis pub/sub channel

    :param classad: dictionary representing classad to publish
    :param channel: channel to publish to
    :param redis_client: a redis client instance to use
    :return: None
    """
    if not redis_client or not channel or not classad:
        return
    redis_client.publish(channel, json.dumps(classad))
    return


def get_redis_client(server=None):
    """
    Get a redis client instance and return it

    :param server: hostname of the Redis server to use
    :return: a redis client instance or None if failure occurs
    """
    if server is None:
        return None
    return redis.StrictRedis(server)


def watch_history_dirs(server=None, channel=None, watchers=None):
    """
    Function that has a loop that watches for changes to condor
    history log files and reads from it when changes occur

    :param server: hostname of Redis server to use
    :param channel: Redis channel to use
    :param watchers: a list or tuple of instantiated HistoryWatcher
                     objects to monitor
    :return: None
    """

    client = get_redis_client(server)
    watchers = restore_state_information(STATE_FILE_PATH)
    files_watched = set()
    for watcher in watchers:
        files_watched.add(watcher.filename)
    while (not os.path.exists(CONDOR_HISTORY_LOG_DIR) or
           not os.path.isdir(CONDOR_HISTORY_LOG_DIR)):
        time.sleep(POLL_INTERVAL)

    dirs = os.listdir(CONDOR_HISTORY_LOG_DIR)
    for directory in dirs:
        history_dir = os.path.join(CONDOR_HISTORY_LOG_DIR, directory)
        if not os.path.isdir(history_dir):
            continue
        history_file = os.path.join(history_dir, 'history')
        if history_file in files_watched:
            continue
        if os.path.isfile(history_file):
            watchers.append(probe_libs.history_watcher.HistoryWatcher(history_file))

    generators = []
    for watcher in watchers:
        generators.append(watcher.next_classad())
    while True:
        for generator in generators:
            classad = next(generator)
            if classad:
                publish_classad(classad, channel, client)
                save_state_information(watchers, STATE_FILE_PATH)


def save_state_information(watchers, filename=None):
    """
    Get state information from watchers and save to specified file
    :param watchers: an array or tuple of HistoryWatcher instances
    :param filename: name of file to save state information in
    :return: True on success, False otherwise
    """
    state_info = []
    if filename is None:
        return True

    for watcher in watchers:
        state_info.append(watcher.get_state())
    with open(filename, 'wb') as filehandle:
        cPickle.dump(state_info, filehandle)
        return True
    return False

def restore_state_information(filename=None):
    """
    Restore state information from a file

    :param filename:
    :return: an (possibly empty) list of watcher objects
    """
    if filename is None:
        return []
    with open(filename, 'rb')  as filehandle:
        state_info = cPickle.load(filehandle)
        watchers = []
        for state in state_info:
            watcher = probe_libs.history_watcher.HistoryWatcher(state[0])
            if watcher.restore_state(state):
                watchers.append(watcher)
        return watchers
    return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create a condor submit file '
                                                 'for processing job log data.')
    parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)
    parser.add_argument('--channel', dest='channel', default=REDIS_CHANNEL,
                        help='Redis channel to publish updates to')
    parser.add_argument('--server', dest='server', default=REDIS_SERVER,
                        help='Redis server to use')
    args = parser.parse_args(sys.argv[1:])
    watch_history_dirs(args.server, args.channel)
