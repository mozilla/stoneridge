#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import bottle
import logging

import stoneridge


@bottle.post('/email')
def email():
    logging.debug('handling email')
    r = bottle.request.forms
    to = r.get('to')
    logging.debug('to: %s' % (to,))
    subject = r.get('subject')
    logging.debug('subject: %s' % (subject,))
    msg = r.get('message')
    logging.debug('message: %s' % (msg,))

    stoneridge.sendmail(to, subject, msg)


def daemon():
    stoneridge.StreamLogger.bottle_inject()
    bottle.run(host='0.0.0.0', port=2255)


@stoneridge.main
def main():
    parser = stoneridge.DaemonArgumentParser()
    parser.parse_args()
    parser.start_daemon(daemon)
