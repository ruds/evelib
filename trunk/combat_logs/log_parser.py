#!/usr/bin/python
# Copyright 2010 Matt Rudary
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Library to parse an eve game log.

It is not unusual for multiple headers to occur in the same log
file. This parser will not catch that, and so may associate events
with the wrong character.

"""

import datetime
import re
import sys


class UTC(datetime.tzinfo):
    """UTC"""
    __ZERO = datetime.timedelta(0)

    def utcoffset(self, dt):
        return __ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return __ZERO


_TIMESTAMP_PATTERN = (
    r'(?P<year>\d{4})\.(?P<month>\d{2})\.(?P<day>\d{2})'
    r' (?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})')


class LogEntry(object):
    """An entry in the log."""
    UNKNOWN = 0
    COMBAT = 1
    INFO = 2
    NOTIFY = 3
    WARNING = 4
    QUESTION = 5
    HINT = 6
    NONE = 7

    def __init__(self, timestamp, entry_type, data):
        self._timestamp = timestamp
        self._entry_type = entry_type
        self._data = data

    __LOG_LINE_RE = re.compile(
        r'^\[ %s \] \((?P<type>[^)]+)\) (?P<data>.+)$'
        % _TIMESTAMP_PATTERN)

    @classmethod
    def parse_line(cls, line):
        """Parse the given line and return a LogEntry.

        Returns None if the current line does not start with a timestamp
        and entry type. This usually indicates a continuation of a previous
        message and is usually because multiple lines of text were shown
        to a user.
        """
        m = cls.__LOG_LINE_RE.match(line)
        if m is None:
            return None
        entry_type = m.group('type')
        y, mo, d, h, mi, s = map(int, m.group('year', 'month', 'day',
                                              'hour', 'min', 'sec'))
        timestamp = datetime.datetime(y, mo, d, h, mi, s, tzinfo = UTC())
        data = m.group('data')
        if entry_type == 'combat':
            return CombatLogEntry(timestamp, data)
        else:
            if entry_type == 'info':
                t = LogEntry.INFO
            elif entry_type == 'notify':
                t = LogEntry.NOTIFY
            elif entry_type == 'warning':
                t = LogEntry.WARNING
            elif entry_type == 'question':
                t = LogEntry.QUESTION
            elif entry_type == 'hint':
                t = LogEntry.HINT
            elif entry_type == 'None':
                t = LogEntry.NONE
            else:
                raise ValueError('Unknown log entry type "%s".' % entry_type)
            return LogEntry(timestamp, t, data)


class CombatLogEntry(LogEntry):
    def __init__(self, timestamp, data):
        LogEntry.__init__(self, timestamp, LogEntry.COMBAT, data)
        self._parse_data()

    @property
    def target(self):
        """The target of this attack."""
        return self._target

    @property
    def attacker(self):
        """The aggressor in this attack."""
        return self._attacker

    @property
    def weapon(self):
        """The weapon used in this attack."""
        return self._weapon

    @property
    def damage(self):
        """The amount of damage dealt by this attack."""
        return self._damage

    __VERB_PHRASES = [
        '%(attacker)s (?:lightly |heavily )?hits %(target)s, %(damage)s\.$',
        '%(attacker)s misses %(target)s completely\.(?!%(damage)s)$',
        '%(attacker)s aims well at %(target)s, %(damage)s\.$',
        '%(attacker)s barely scratches %(target)s, %(damage)s\.$',
        '%(attacker)s places an excellent hit on %(target)s, %(damage)s\.$',
        ('%(attacker)s lands a hit on %(target)s which glances off,'
         ' %(damage)s\.$'),
        '%(attacker)s is well aimed at %(target)s, %(damage)s\.$',
        '%(attacker)s barely misses %(target)s\.(?!%(damage)s)$',
        '%(attacker)s glances off %(target)s, %(damage)s\.$',
        '%(attacker)s strikes %(target)s perfectly, %(damage)s\.$',
        '%(attacker)s perfectly strikes %(target)s, %(damage)s\.$',
        ]

    __ATTACKER_PATTERNS = [ '(?P<attacker>Your) (?:group of )?(?P<weapon>.*)',
                            '(?P<weapon>.*) belonging to (?P<attacker>.*)',
                            '(?P<attacker>.*)(?P<weapon>)' ]

    __VERB_PHRASE_RES = [
        re.compile(vp % { 'attacker': '(?:<color[^>]*>)?%s' % a,
                          'target': '(?P<target>.*)',
                          'damage': r'[^,]*(?P<damage>\d+\.\d+)? damage' })
        for vp in __VERB_PHRASES
        for a in __ATTACKER_PATTERNS
        ]

    __stats = [0] * len(__VERB_PHRASE_RES)

    @classmethod
    def print_stats(cls):
        """Print statistics about types of log entries."""
        stats_table = zip(cls.__stats, ((vp, a)
                                        for vp in cls.__VERB_PHRASES
                                        for a in cls.__ATTACKER_PATTERNS))
        print 'Count\tVerb Phrase\n\tAttacker Phrase\n'
        for count, (vp, a) in stats_table:
            print '%d\t%s\n\t%s\n' % (count, vp, a)

    def _parse_data(self):
        m = None
        i = 0
        for rex in self.__VERB_PHRASE_RES:
            m = rex.match(self._data)
            if m is not None:
                CombatLogEntry.__stats[i] += 1
                break
            i += 1
        if m is None:
            raise ValueError('Could not parse """%s""".' % self._data)

        self._target = m.group('target')
        self._attacker = m.group('attacker')
        self._weapon = m.group('weapon')
        self._damage = m.group('damage')
        if self._damage is None:
            self._damage = 0


class Log(object):
    """A log consists of some metadata and a sequence of log entries."""
    def __init__(self, listener, start_time, log_entries):
        self._listener = listener
        self._start_time = start_time
        self.log_entries = list(log_entries)

    @classmethod
    def parse_log(cls, log_file):
        """Parse the given log file.

        Args:
          log_file: A filename or file-like object that contains a
              single gamelog. If log_file is a file-like object, it
              will be closed before this function returns.

        Returns:
          A Log object.

        """
        if isinstance(log_file, basestring):
            infile = open(log_file, 'r')
        else:
            infile = log_file

        try:
            listener, timestamp = cls.__read_header(infile)
            return Log(listener, timestamp,
                       (LogEntry.parse_line(l.rstrip()) for l in infile))
        finally:
            infile.close()

    __MINUSES_RE = re.compile('^-+$')
    __GAMELOG_RE = re.compile('Gamelog')
    __LISTENER_RE = re.compile('Listener: (.*)')
    __SESSION_RE = re.compile(
        'Session started: %s' % _TIMESTAMP_PATTERN)

    @classmethod
    def __read_header(cls, infile):
        try:
            if not cls.__MINUSES_RE.match(infile.next().rstrip()):
                raise ValueError('Missing --- line at start of file.')
            if not cls.__GAMELOG_RE.search(infile.next().rstrip()):
                raise ValueError('Missing "Gamelog" line in header.')
            # Empty logs don't have listeners...
            maybe_listener_line = infile.next().rstrip()
            m = cls.__LISTENER_RE.search(maybe_listener_line)
            if m is None:
                listener = 'Unknown'
                session_start_line = maybe_listener_line
            else:
                listener = m.group(1)
                session_start_line = infile.next().rstrip()
            m = cls.__SESSION_RE.search(session_start_line)
            if m is None:
                raise ValueError('Missing "Session started" line in header.')
            y, mo, d, h, mi, s = map(int, m.group('year', 'month', 'day',
                                                  'hour', 'min', 'sec'))
            timestamp = datetime.datetime(y, mo, d, h, mi, s, tzinfo = UTC())
            if not cls.__MINUSES_RE.match(infile.next().rstrip()):
                raise ValueError('Missing --- line to end header.')

        except StopIteration:
            raise ValueError('Cannot parse header -- too few lines.')
        return listener, timestamp


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        try:
            log = Log.parse_log(filename)
            print 'Log %s had %d lines.' % (filename, len(log.log_entries))
        except ValueError, e:
            print >>sys.stderr, 'Error parsing %s: %s.' % (filename, e)

    CombatLogEntry.print_stats()

