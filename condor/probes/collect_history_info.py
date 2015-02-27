#!/usr/bin/env python

import sys
import time
import os
import json
import re

import redis

REDIS_SERVER = 'db.mwt2.org'
REDIS_CHANNEL = 'osg-connect-history'
CONDOR_HISTORY_LOG = '/var/lib/condor/spool/history'
# number of seconds to wait before polling history file
POLL_INTERVAL = 60

def publish_classad(classad, channel, redis_client):
    """
    Publishes a classad to a Redis pub/sub channel

    :param classad: dictionary representing classad to publish
    :param redis_client: a redis client instance to use
    :return: None
    """
    if not redis_client or not channel or not classad:
        return
    redis_client.publish(channel, json.dumps(classad))
    return

def get_redis_client():
    """
    Get a redis client instance and return it

    :return: a redis client instance or None if failure occurs
    """
    return redis.StrictRedis(REDIS_SERVER)


# used in parse_classad
completion_re = re.compile(r'\*\*\*\s+Offset\s+=\s+\d+.*CompletionDate\s+=\s+(\d+)')


def parse_classad(buffer):
    """
    Parse and return all classads found in buffer and returning any left
    over text

    :param buffer: string with
    :return: tuple (classads, string) with a list of classads and remaining
    part of the buffer
    """

    classad = {}
    classads = []
    remaining_buffer = ""
    for line in buffer:
        if not line:
            break
        match = completion_re.match(line)
        if match is not None:
            classad['CompletionDate'] = int(match.group(1))
            classads.append(classad)
            classad = {}
            remaining_buffer = ""
        else:
            (key, value) = line.split('=')
            classad[key.strip()] = value.strip()
            remaining_buffer += line
    return classads, remaining_buffer


def watch_history_file():
    """
    Function that has a loop that watches for changes to condor
    history log files and reads from it when changes occur

    :return: None
    """
    while (not os.path.exists(CONDOR_HISTORY_LOG) or
               not os.path.isfile(CONDOR_HISTORY_LOG)):
        time.sleep(1)
    log_file = os.open(CONDOR_HISTORY_LOG)
    file_stat = os.stat(CONDOR_HISTORY_LOG)
    current_inode = file_stat.st_ino
    client = get_redis_client()
    buffer = ""
    while True:
        where = log_file.tell()
        line = log_file.readline()
        if not line:
            new_stat = os.stat(CONDOR_HISTORY_LOG)
            if current_inode != new_stat.st_ino:
                log_file.close()
                current_inode = new_stat.st_ino
                log_file = open(CONDOR_HISTORY_LOG)
            time.sleep(60)
            log_file.seek(where)
        else:
            buffer += line
            classads, buffer = parse_classad(buffer)
            if classads:
                for classad in classads:
                    publish_classad(classad, REDIS_CHANNEL, client)



