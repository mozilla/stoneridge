#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
import requests

import srworker
import stoneridge


class StoneRidgeWebWorker(srworker.StoneRidgeWorker):
    def __init__(self):
        self.url = stoneridge.get_config('mqproxy', 'url')
        self.setup()

    def run(self):
        res = requests.get(self.url)

        if res.status_code != 200:
            logging.error('Got non-200 response: %s %s (text %s)' %
                          (res.status_code, res.reason, res.text))
            return

        logging.debug('Got response %s' % (res.text,))

        if not res.text:
            logging.debug('No entries waiting!')
            return

        args = json.loads(res.text)

        logging.debug('Handling request')

        self.handle(**args)

        logging.debug('Done')


@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    parser.parse_args()

    worker = StoneRidgeWebWorker()
    try:
        worker.run()
    except:
        logging.exception('Error running this time')
