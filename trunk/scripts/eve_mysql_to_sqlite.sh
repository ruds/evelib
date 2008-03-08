#!/bin/bash
# Copyright 2008
# Matt Rudary (ruds@boxbe.com)
#
# Read some SQL from sqlfile... and commit it to dbfile, an sqlite3
# database file. If no sqlfiles are given on the command line, read
# from standard input.
# This is designed specifically for the mysql dump created by the
# developers of Eve Online, and is nowhere near general purpose.
#
# The BEGIN; and COMMIT; lines are very important. With them, a reasonable
# machine can process the entire DB in less than five minutes. Without them,
# it could take hours or more.
#
# EXAMPLES:
# If you want to create a big db file that has all the tables from the
# Trinity 1.0 release, run
# $ tar -jOxf trinity_1.0_sql_mysql5.tar.bz2|./eve_mysql_to_sqlite.sh trinity.db
#
# If you've already decompressed the tarball, you can create a db of
# all the map related data by running
# $ ./eve_mysql_to_sqlite.sh trinity_map.db map*.sql

TMPDIR=/tmp

echo "Usage: $0 dbfile [sqlfile ...]" 2>&1

DBFILE="$1"
shift

TEMPBEGIN=$TMPDIR/begin.$$.$RANDOM
TEMPCOMMIT=$TMPDIR/commit.$$.$RANDOM

echo 'begin;' > $TEMPBEGIN
echo 'commit;' > $TEMPCOMMIT

HYPHEN=-
if [ $# -eq 0 ]; then
  echo option 1
  ARG=HYPHEN
else
  echo option 2
  ARG=@
fi

cat $TEMPBEGIN "${!ARG}" $TEMPCOMMIT \
  | perl -n \
      -e 'next if /DROP/;' \
      -e 'next if /LOCK/;' \
      -e 'next if /KEY/ && not /PRIMARY/;' \
      -e 's/,$// if /PRIMARY/;' \
      -e 's/\bint\b/integer/gi;' \
      -e 's/`//g;' \
      -e 's/\\.//g;' \
      -e 's/^\).*;/);/;' \
      -e 'if(/(insert[^(]*)/i){$p=$1;s/\),/);\n$p/g;print;}else{print}' \
  | sqlite3 $DBFILE

rm $TEMPBEGIN $TEMPCOMMIT
