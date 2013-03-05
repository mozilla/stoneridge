#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import bottle

import stoneridge


@bottle.post('/email')
def email():
    r = bottle.request
    to = r.forms.get('to')
    subject = r.forms.get('subject')
    msg = r.forms.get('message')

    stoneridge.sendmail(to, subject, msg)


def daemon():
    stoneridge.StreamLogger.bottle_inject()
    bottle.run('0.0.0.0', port=2255)


@stoneridge.main
def main():
    parser = stoneridge.DaemonArgumentParser()
    parser.parse_args()
    parser.start_daemon(daemon)
