#!/bin/bash
# Copyright 2008 Matt Rudary
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
# Read some SQL from sqlfile... and commit it to dbfile, an sqlite3
# database file. If no sqlfiles are given on the command line, read
# from standard input.
# This is designed specifically for the MS-SQL dump created by the
# developers of Eve Online, and is nowhere near general purpose. This
# should probably be preferred over the mysql script, as the MS-SQL is
# produced directly by the devs and the MySQL dump is derived from that.
# Also, there's much less alteration needed to translate from MS-SQL.
# The only possible advantage of the MySQL dumps is that it might be
# indexed better -- whoever did it selected some non-default primary keys.
#
# EXAMPLES:
# If you want to create a big db file that has all the tables from the
# Trinity 1.0 release, run
# $ tar -jOxf trinity_1.0_sql.zip |./eve_mssql_to_sqlite.sh trinity.db
#
# If you've already decompressed the tarball, you can create a db of
# all the map related data by running
# $ ./eve_mssql_to_sqlite.sh trinity_map.db dbo_map*.sql

if [ $# -lt 1 ]; then
    echo "Usage: $0 dbfile [sqlfile ...]" 2>&1
fi

DBFILE="$1"
shift

(  echo "BEGIN;"
   cat "$@" \
       | perl -n \
       -e 'next if /COMMIT/;' \
       -e 's/dbo\.//;' \
       -e 's/true/1/gi; s/false/0/gi;' \
       -e 'print;'
   echo 'COMMIT;' ) \
| sqlite3 $DBFILE
