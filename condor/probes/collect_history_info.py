#!/usr/bin/env python

import time
import os
import json
import re
import cStringIO

import redis

REDIS_SERVER = 'db.mwt2.org'
REDIS_CHANNEL = 'osg-connect-history'
CONDOR_HISTORY_LOG = '/var/lib/condor/spool/history'
# number of seconds to wait before polling history file
POLL_INTERVAL = 60
JOB_STATUS = {'0': 'Unexpanded',
              '1': 'Idle',
              '2': 'Running',
              '3': 'Removed',
              '4': 'Completed',
              '5': 'Held',
              '6': 'Submission Error'}
JOB_UNIVERSE = {'0': 'Min',
                '1': 'Standard',
                '2': 'Pipe',
                '3': 'Linda',
                '4': 'PVM',
                '5': 'Vanilla',
                '6': 'PVMD',
                '7': 'Scheduler',
                '8': 'MPI',
                '9': 'Grid',
                '10': 'Java',
                '11': 'Parallel',
                '12': 'Local',
                '13': 'Max'}

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
    temp = cStringIO.StringIO(buffer)
    for line in temp:
        if not line:
            break
        match = completion_re.match(line)
        if match is not None:
            classad['CompletionDate'] = int(match.group(1))
            classads.append(classad)
            classad = {}
            remaining_buffer = ""
        else:
            fields = line.split('=')
            if len(fields) != 2:
                continue
            key = fields[0].strip()
            value = fields[1].strip()
            if key in classad:
                try:
                    value = int(value)
                    if value > classad[key]:
                        classad[key] = temp
                        continue
                except ValueError:
                    classad[key.strip()] = value.strip()
                    continue
            if value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            if key == 'JobStatus':
                value = JOB_STATUS[value]
            if key == 'JobUniverse':
                value = JOB_UNIVERSE[value]
            classad[key] = value
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
        time.sleep(POLL_INTERVAL)
    log_file = open(CONDOR_HISTORY_LOG)
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
            time.sleep(POLL_INTERVAL)
            log_file.seek(where)
        else:
            buffer += line
            classads, buffer = parse_classad(buffer)
            if classads:
                for classad in classads:
                    publish_classad(classad, REDIS_CHANNEL, client)


if __name__ == "__main__":
   watch_history_file() 
