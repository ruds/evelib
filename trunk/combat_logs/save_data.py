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

"""A webapp.RequestHandler that returns its input as a file to be saved."""

import re

from django.utils import simplejson
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

_SANE_RE = re.compile('^[-_.A-Za-z0-9]+$')
def sanitize(s):
    """Returns s as an ascii-encoded str if safe, otherwise the empty string.

    Safe: An ascii-encoded string containing letters, numbers, and any of
    '-', '_', and '.'.

    """
    try:
        ascii = s.encode('ascii')
    except UnicodeError:
        return ''

    if _SANE_RE.match(ascii):
        return ascii
    else:
        return ''

class SaveData(webapp.RequestHandler):
    def post(self):
        self.response.headers['Content-Type'] = sanitize(self.request.get(
            'content_type', default_value='application/octet-stream'))
        filename = sanitize(self.request.get('filename', default_value=''))
        disposition_params = {}
        if filename:
            disposition_params['filename'] = filename
        self.response.headers.add_header(
            'Content-Disposition', 'attachment', **disposition_params)

        self.response.out.write(self.request.get('content', default_value=''))
        

application = webapp.WSGIApplication([('/save_data', SaveData)])


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()
