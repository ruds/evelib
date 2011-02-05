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

"""Serve the log parser on appengine."""

import logging
import StringIO

from django.utils import simplejson
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import combat_log_analyzer
import log_parser


class CustomJSONEncoder(simplejson.JSONEncoder):
    def default(self, obj):
        try:
            return combat_log_analyzer.serialize(obj)
        except TypeError:
            return simplejson.JSONEncoder.default(self, obj)


class ParseFile(webapp.RequestHandler):
    def post(self):
        log_content = self.request.get('logfile')
        logfile = StringIO.StringIO(log_content)

        self.response.headers['Content-Type'] = 'text/html; charset=utf-8'
        output_obj = {}
        try:
            parsed = log_parser.Log.parse_log(logfile)
            output_obj['arr'] = combat_log_analyzer.extract_streams(parsed)
        except ValueError, e:
            logging.error('Could not parse file: %s\n%s' % (e, log_content))
            output_obj['error'] = "Can't parse file: %s" % e
        data = simplejson.dumps(output_obj, cls=CustomJSONEncoder)
        self.response.out.write('<textarea>\n%s\n</textarea>' % data)


application = webapp.WSGIApplication([('/parse_file', ParseFile)])


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()
