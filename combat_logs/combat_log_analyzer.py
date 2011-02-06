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

"""Library to analyze Eve combat logs."""

import datetime
import re
import time

import log_parser


class DamageStream(object):
    def __init__(self, attacker, target, damage,
                 ticker='Unknown', weapon='Unknown', enemy_ships=[]):
        """Initialize a Damage Stream.

        attacker, target, ticker, and weapon are arbitrary
        strings. enemy_ships is an iterable of strings. damage is a
        sequence of pairs (timestamp, amount), where timestamp is a
        datetime.datetime and amount is a number. The timestamps must
        be in non-decreasing order.

        """
        self._attacker = attacker
        self._target = target
        self._damage = list(damage)
        self._ticker = ticker
        self._weapon = weapon or 'Unknown'
        self._enemy_ships = ', '.join(enemy_ships) or 'Unknown'
        self._total_damage = sum(d[1] for d in self._damage)
        if self._damage:
            self._start_time = self._damage[0][0]
            self._end_time = self._damage[-1][0]
        else:
            self._start_time = None
            self._end_time = None

    @property
    def attacker(self):
        """The character and/or ship dealing this damage."""
        return self._attacker

    @property
    def target(self):
        """The character and/or ship receiving this damage."""
        return self._target

    @property
    def ticker(self):
        """The corp/alliance ticker of the enemy, if known."""
        return self._ticker

    @property
    def weapon(self):
        """The weapon dealing this damage, if known."""
        return self._weapon

    @property
    def damage(self):
        """An iterator generating a sequence of (timestamp. amount) pairs."""
        return iter(self._damage)

    @property
    def total_damage(self):
        return self._total_damage

    @property
    def enemy_ships(self):
        """A string containing a list of ships used by the enemy or Unknown."""
        return self._enemy_ships

    @property
    def start_time(self):
        """The earliest timestamp in this damage stream, or None."""
        return self._start_time

    @property
    def end_time(self):
        """The latest timestamp in this damage stream, or None."""
        return self._end_time

    def to_json_serializable(self):
        """Convert this DamageStream to an object json.dump can serialize."""
        return {
            'attacker': self.attacker,
            'target': self.target,
            'weapon': self.weapon,
            'ticker': self.ticker,
            'damage': list(self.damage),
            'enemy_ships': self.enemy_ships,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'total_damage': self.total_damage,
            }


def combat_entries(log):
    for e in log.log_entries:
        if e.entry_type == log_parser.LogEntry.COMBAT:
            yield e


# By default, the enemy's id string looks like
# Char'acter Name [CORP]&lt;.ALL.&gt;(Shiptype mark IV)
_MIDDLE_CHAR = "['A-Za-z0-9]"
_FIRST_LAST_CHAR = '[A-Za-z0-9]'
_TICKER = "[-'. A-Za-z0-9]"
_ENEMY_RE = re.compile(
    (r'\s*(?P<name>%(_FIRST_LAST_CHAR)s%(_MIDDLE_CHAR)s*' # first name
     r'(?: %(_MIDDLE_CHAR)s*)??%(_FIRST_LAST_CHAR)s)' # second name
     r'\s*(?:\[(?P<corp>%(_TICKER)s+)\])?' # corp ticker
     r'\s*(?:&lt;(?P<alliance>%(_TICKER)s+)&gt;)?' # alliance ticker
     r"\s*(?:'.*')?" # ship name
     r'\s*\((?P<ship>[A-Za-z ]+)\)\s*$') % locals()) # ship type
_DUPE_NAME_RE = re.compile(r"([^ ]+) '\1")

def enemy_info(id_string):
    """Given a log id string, try to extract ship, corp, alliance info.

    Returns a tuple (name, ship, corp_and_alliance). ship and
    corp_and_alliance may both be None.

    """
    default_value = (id_string, None, None)
    m = _ENEMY_RE.match(id_string)
    if m is None:
        return default_value
    name, ship, corp, alliance = m.group('name', 'ship', 'corp', 'alliance')

    if corp is None:
        corp = ''
        # If you have a character called Name in an NPC corp and
        # they're flying a ship named "Name's Purifier", the previous
        # re might parse their name into "Name 'Name" and their ship
        # name into "s Purifier". Let's fix that.
        if ship is not None:
            m = _DUPE_NAME_RE.match(name)
            if m:
                name = m.group(1)
    if alliance is None:
        return (name, ship, corp)
    else:
        return (name, ship, '%s (%s)' % (corp, alliance))


def extract_streams(log):
    """Extract damage streams from the given log_parser.Log."""
    # key = (weapon, enemy_name), value = [(timestamp, damage_amount),...]
    your_damage_streams = {}
    enemy_damage_streams = {}
    # key = name, value = (ticker, set([ship1, ship2,...]))
    enemy_info_map = {}
    for e in combat_entries(log):
        if e.attacker.strip().lower() == 'you':
            enemy = e.target
            enemy_name, ship, ticker = enemy_info(enemy)
            stream = your_damage_streams.setdefault((e.weapon, enemy_name), [])
        else:
            enemy = e.attacker
            enemy_name, ship, ticker = enemy_info(enemy)
            stream = enemy_damage_streams.setdefault((e.weapon, enemy_name), [])

        timestamp = e.timestamp
        amount = e.damage
        if stream and stream[-1][0] == timestamp:
            stream[-1] = (timestamp, stream[-1][1] + amount)
        else:
            stream.append((timestamp, amount))

        if ship is not None:
            t, ship_types = enemy_info_map.setdefault(enemy_name,
                                                      (ticker, set()))
            ship_types.add(ship)

    damage_streams = []
    def add_streams(stream_map, enemy_attacks):
        for k, stream in stream_map.iteritems():
            weapon, enemy = k
            ticker, ships = enemy_info_map.setdefault(enemy, ('Unknown', []))
            if enemy_attacks:
                attacker = enemy
                target = 'You'
            else:
                attacker = 'You'
                target = enemy
            damage_streams.append(
                DamageStream(attacker, target, stream, ticker, weapon, ships))

    add_streams(your_damage_streams, False)
    add_streams(enemy_damage_streams, True)

    return damage_streams


def serialize(obj):
    if isinstance(obj, datetime.datetime):
        return time.mktime(obj.timetuple()) * 1000
    elif isinstance(obj, DamageStream):
        return obj.to_json_serializable()
    else:
        raise TypeError(
            'Object of type %s with value of %s is not JSON serializable'
            % (type(obj), repr(obj)))


if __name__ == '__main__':
    import json
    import sys
    html_template = open('template.html', 'r').read()
    log = log_parser.Log.parse_log(sys.argv[1])
    streams = extract_streams(log)
    data = json.dumps(streams, default=serialize)
    print html_template % { 'json': data }
