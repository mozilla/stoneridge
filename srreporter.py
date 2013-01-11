#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import base64
import dzclient
import json
import logging
import os

import stoneridge


class StoneRidgeReporter(stoneridge.QueueListener):
    def setup(self):
        self.host = stoneridge.get_config('report', 'host')
        self.project = stoneridge.get_config('report', 'project')
        self.key = stoneridge.get_config('report', 'key')
        self.secret = stoneridge.get_config('report', 'secret')
        self.archives = stoneridge.get_config('report', 'archives')

        logging.debug('report host: %s' % (self.host,))
        logging.debug('project: %s' % (self.project,))
        logging.debug('oauth key: %s' % (self.key,))
        logging.debug('oauth secret: %s' % (self.secret,))
        logging.debug('archives: %s' % (self.archives,))

    def save_data(self, srid, results, metadata_b64):
        archivedir = os.path.join(self.archives, srid)
        os.makedirs(archivedir)

        results_file = os.path.join(archivedir, 'results.json')
        with file(results_file, 'w') as f:
            f.write(results)

        metadata = base64.b64decode(metadata_b64)
        metadata_file = os.path.join(archivedir, 'metadata.zip')
        with file(metadata_file, 'wb') as f:
            f.write(metadata)

    def handle(self, srid, results, metadata_b64)):
        logging.debug('uploading results for %s' % (srid,))

        try:
            result_dict = json.loads(results)
        except:
            # This is crap, ignore it
            logging.error('bad results dict: %s' % (results,))
            self.save_data(srid, results, metadata_b64)
            return

        for name, contents in result_dict.iteritems():
            try:
                dataset = json.loads(contents)
                logging.debug('read data: %s' % (dataset,))
            except:
                # This one is crap, ignore it
                logging.error('bad json: %s' % (contents,))
                continue

            logging.debug('uploading data')
            request = dzclient.DatazillaRequest('https', self.host,
                    self.project, self.key, self.secret)
            response = request.send(dataset)
            logging.debug('got status code %s' % (response.status,))
            if response.status != 200:
                logging.error('bad http status %s for %s' % (response.status, srid))

            try:
                result = json.load(response)
            except:
                result = ''
            logging.debug('got result %s' % (result,))
            if result['status'] != 'well-formed JSON stored':
                logging.error('bad status for %s: %s' % (srid, result['status']))

        self.save_data(srid, results, metadata_b64)


def daemon():
    reporter = StoneRidgeReporter(stoneridge.OUTGOING_QUEUE)
    reporter.run()


@stoneridge.main
def main():
    parser = stoneridge.DaemonArgumentParser()
    args = parser.parse_args()

    parser.start_daemon(daemon)
