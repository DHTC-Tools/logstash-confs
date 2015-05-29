#!/usr/bin/env python

# Copyright 2015 University of Chicago
# Available under Apache 2.0 License

import time
import os
import json
import argparse
import sys

import redis

import probe_libs.history_watcher

VERSION = '0.5'
REDIS_SERVER = 'db.mwt2.org'
REDIS_CHANNEL = 'osg-connect-history'
CONDOR_HISTORY_LOG_DIR = '/var/lib/condor/'
# number of seconds to wait before polling history file
POLL_INTERVAL = 60


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



def watch_history_dirs(server=None, channel=None):
    """
    Function that has a loop that watches for changes to condor
    history log files and reads from it when changes occur

    :param server: hostname of Redis server to use
    :param channel: Redis channel to use
    :return: None
    """

    while (not os.path.exists(CONDOR_HISTORY_LOG_DIR) or
           not os.path.isdir(CONDOR_HISTORY_LOG_DIR)):
        time.sleep(POLL_INTERVAL)

    dirs = os.listdir(CONDOR_HISTORY_LOG_DIR)
    watchers = []
    client = get_redis_client(server)
    for directory in dirs:
        history_dir = os.path.join(CONDOR_HISTORY_LOG_DIR, directory)
        if not os.path.isdir(history_dir):
            continue
        history_file = os.path.join(history_dir, 'history')
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
