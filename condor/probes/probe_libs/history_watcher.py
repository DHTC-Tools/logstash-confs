# Copyright 2015 University of Chicago
# Available under Apache 2.0 License

import os
import cStringIO
import re
import time

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

class HistoryWatcher:
    """
    Watches a history file and gets latest classad from it
    """

    def __init__(self, filename=None):
        """
        Initializer

        :param filename: path to history file that should be watched
        """

        self._filename = filename
        self._buff = ""
        self._current_inode = 0
        self._filehandle = None
        # used in parse_classad
        self._completion_re = re.compile(r'\*\*\*\s+Offset\s+=\s+\d+.*CompletionDate\s+=\s+(\d+)')

    @filename.setter
    def filename(self, filename=None):
        """
        Set file to watch for the class

        :param filename: path to history file that should be watched
        """
        self._filename = filename

    @property
    def filename(self):
        """
        Return the filename that's being watched
        :return: filename of watched file
        """
        return self._filename

    def next_classad(self):
        """
        Generator that gets the latest classad from watched file

        :return: a dict with classads
        """
        if not self._filename:
            yield {}

        if not os.path.isfile(self._filename):
            yield {}

        if self._filehandle is None:
            try:
                self._filehandle = open(self._filename)
            except IOError:
                yield {}
        if self._current_inode == 0:
            file_stat = os.stat(self._filename)
            self._current_inode = file_stat.st_ino

        while True:
            where = self._filehandle.tell()
            line = self._filehandle.readline()
            if not line:
                try:
                    new_stat = os.stat(self._filename)
                except OSError:
                    # file may not be there due to rotation, wait a while and check again
                    time.sleep(0.5)
                    continue
                if self._current_inode != new_stat.st_ino:
                    self._filehandle.close()
                    self._current_inode = new_stat.st_ino
                    self._filehandle = open(self._filename)
                    where = self._filehandle.tell()
                self._filehandle.seek(where)
                # give up control and then pause when starting again
                yield {}
                time.sleep(30)
            else:
                self._buff += line
                classads, self._buff = self.__parse_classad(self._buff)
                if classads:
                    for classad in classads:
                        yield classad
                else:
                    yield {}

    def __parse_classad(self, classad_string):
        """
        Parse a string into a dict with HTCondor classads

        :param classad_string: string with classads in it
        :return: tuple (classads, string) with a list of classads and remaining
                 part of the buffer
        """
        classad = {}
        classads = []
        remaining_buffer = ""
        temp = cStringIO.StringIO(classad_string)
        for line in temp:
            if not line:
                break
            match = self._completion_re.match(line)
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
                        else:
                            continue
                    except ValueError:
                        classad[key.strip()] = value.strip()
                        continue
                if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                    value = value[1:-1]
                if key == 'JobStatus':
                    value = JOB_STATUS[value]
                if key == 'JobUniverse':
                    value = JOB_UNIVERSE[value]
                classad[key] = value
                remaining_buffer += line
        return classads, remaining_buffer

    def get_state(self):
        """
        Create a record of current state that can be used at a later point
        to restore file watcher to the same position if possible

        :return: a tuple (filename, inode, position) with state information
        """

        return self._filename, self._current_inode, self._filehandle.tell()

    def restore_state(self, state_tuple):
        """
        Restore state information from a state tuple so that file watching
        can be continued, note, this may not succeed if the file is missing
        or has been rotated

        :param state_tuple: a tuple with filename, inode, and file_position
        :return: True if state has been restored, False otherwise
        """

        if not os.path.isfile(state_tuple[0]):
            self._filename = state_tuple[0]
            self._current_inode = 0
            return False
        self._filename = state_tuple[0]
        try:
            self._filehandle = open(self._filename)
        except IOError:
            return False
        current_inode = os.stat(self._filename).st_ino
        if current_inode != state_tuple[1]:
            return False
        self._current_inode = state_tuple[1]
        self._filehandle.seek(state_tuple[2])
