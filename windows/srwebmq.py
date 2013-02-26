#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import bottle
import logging
import sqlite3
import sys

import stoneridge


conn = None  # Persistent connection for sqlite file


class StreamLogger(object):
    """Redirect a stream to a logger
    """
    def __init__(self, logger):
        self.logger = logger

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(logging.DEBUG, line.rstrip())


@bottle.route('/get_next')
def get_next():
    cur = conn.cursor()
    cur.execute('SELECT id, config FROM runs WHERE done = ? ORDER BY id ASC '
                'LIMIT 1', (False,))
    res = cur.fetchall()
    if res:
        id_, config = res[0]
        logging.debug('Found entry %s' % (config,))
        cur.execute('UPDATE runs SET done = ? WHERE id = ?', (True, id_))
        conn.commit()
    else:
        logging.debug('No entries waiting')
        config = ''

    logging.debug('Returning %s' % (config,))
    return config


def daemon():
    global conn
    dbfile = stoneridge.get_config('mqproxy', 'db')
    conn = sqlite3.connect(dbfile)

    # Do some nasty hackery to make sure everything bottle prints goes to our
    # log, too
    streamlogger = StreamLogger(logging.getLogger())
    sys.stdout = sys.stderr = streamlogger
    bottle._stdout = bottle._stderr = streamlogger.write

    port = stoneridge.get_config_int('mqproxy', 'port')
    bottle.run(host='0.0.0.0', port=port)


@stoneridge.main
def main():
    parser = stoneridge.DaemonArgumentParser()
    parser.parse_args()

    parser.start_daemon(daemon)
