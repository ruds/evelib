#!/usr/bin/python

import argparse
import sqlite3
import sys

def read_flags(argv):
    parser = argparse.ArgumentParser(
        prog=argv[0],
        description=('Build a table that contains all of the solar systems '
                     'and how far they are from Jita.'))
    parser.add_argument('dbfile', metavar='<dbfile>',
                        help='The file containing the Eve static data dump.')
    return parser.parse_args(argv[1:])

def read_graph(conn):
    """Read the jump graph from the database.

    Args:
        conn: A Connection.

    Returns:
        A map from solar system name to a list of adjacent solar systems.
        E.g. 'Rens' -> ['Abudban', 'Odatrik', 'Frarn']
    """
    cursor = conn.cursor()
    cursor.execute('SELECT s.solarSystemName, m.itemID '
                   'FROM mapdenormalize m '
                   'JOIN mapsolarsystems s '
                   'ON s.solarSystemID = m.solarSystemID '
                   'WHERE m.groupID = 10;')
    locations = {} # gate id -> solar system
    for row in cursor:
        locations[row[1]] = row[0]

    cursor.execute('SELECT stargateID, celestialID FROM mapjumps;')

    adjacency = {} # solar system -> [adjacent solar systems]
    for row in cursor:
        adjacency.setdefault(locations[row[0]], []).append(locations[row[1]])

    return adjacency

def relax(d, p, u, v, w):
    if d[v] > d[u] + w:
        d[v] = d[u] + w
        p[v] = u

def compute_distance(adjacency, start='Jita'):
    """Computes the distance from each system to the start system.

    Yields:
        Tuples (SolarSystem, Distance, Next System), where
        Next System is the next system to travel to on a route through
        SolarSystem to the start system.
    """
    d = {}
    p = {}
    for system in adjacency.iterkeys():
        d[system] = 1000000
        p[system] = None
    d[start] = 0
    q = dict(d)
    while q:
        u = None
        ud = 1000000
        for k, v in q.iteritems():
            if u is None or v < ud:
                ud = v
                u = k
        del q[u]
        for v in adjacency[u]:
            if v in q:
                relax(d, p, u, v, 1)
                q[v] = d[v]
    for k, v in d.iteritems():
        yield k, v, p[k]

def write_table(conn, entries):
    cursor = conn.cursor()
    cursor.execute('SELECT solarSystemName, solarSystemID '
                   'FROM mapsolarsystems;')
    ids = { None: 'None' }
    for row in cursor:
        ids[row[0]] = row[1]
    f = lambda s: s or 0

    cursor.execute('CREATE TABLE rudsmapjitadistance ('
                   ' solarSystemID INT(11) PRIMARY KEY, '
                   ' solarSystemName VARCHAR(100), '
                   ' distance INT(11), '
                   ' nextSolarSystemID INT(11), '
                   ' nextSolarSystemName VARCHAR(100));')
    for s, d, n in entries:
        cursor.execute('INSERT INTO rudsmapjitadistance '
                       'VALUES (?, ?, ?, ?, ?);',
                       (ids[s], s, d, ids[n], f(n)))

def main(argv):
    flags = read_flags(argv)
    with sqlite3.connect(flags.dbfile) as conn:
        write_table(conn, compute_distance(read_graph(conn)))
        conn.commit()

if __name__ == '__main__':
    main(sys.argv)
