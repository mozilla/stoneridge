#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
import requests
import time

import srworker
import stoneridge


class StoneRidgeWebWorker(srworker.StoneRidgeWorker):
    def __init__(self):
        self.url = stoneridge.get_config('mqproxy', 'url')
        self.setup()

    def run(self):
        handled = True

        while True:
            if not handled:
                time.sleep(5)

            handled = False

            try:
                res = requests.get(self.url)
            except:
                logging.exception('Error getting events')
                continue

            if res.status_code != 200:
                logging.error('Got non-200 response: %s %s (text %s)' %
                              (res.status_code, res.reason, res.text))
                continue

            logging.debug('Got response %s' % (res.text,))

            if not res.text:
                logging.debug('No entries waiting!')
                continue

            try:
                args = json.loads(res.text)
            except:
                logging.exception('Error loading result as json')
                continue

            logging.debug('Handling request')

            handled = True
            try:
                self.handle(**args)
            except:
                logging.exception('Error handling request')
                continue

            logging.debug('Done')


@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    parser.parse_args()

    worker = StoneRidgeWebWorker()
    worker.run()
