#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
import sqlite3

import stoneridge


class StoneRidgeMQProxy(stoneridge.QueueListener):
    def setup(self):
        self.dbfile = stoneridge.get_config('mqproxy', 'db')
        self.conn = sqlite3.connect(self.dbfile)

    def handle(self, **kwargs):
        logging.debug('Got new windows queue entry: %s' % (kwargs,))
        cursor = self.conn.cursor()
        config = json.dumps(kwargs)
        cursor.execute('INSERT INTO runs (config, done) VALUES (?, ?)',
                       (config, False))
        self.conn.commit()
        logging.debug('Inserted into persistent queue')


def daemon():
    proxy = StoneRidgeMQProxy(stoneridge.CLIENT_QUEUES['windows'])
    proxy.run()


@stoneridge.main
def main():
    parser = stoneridge.DaemonArgumentParser()
    parser.parse_args()

    parser.start_daemon(daemon)
