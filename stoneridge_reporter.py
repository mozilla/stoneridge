#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import dzclient
import glob
import json
import logging
import os
import shutil

import stoneridge

class StoneRidgeReporter(object):
    def __init__(self):
        self.rootdir = stoneridge.get_config('server', 'uploads')
        self.pattern = os.path.join(self.rootdir, '*.json')
        self.host = stoneridge.get_config('report', 'host')
        self.project = stoneridge.get_config('report', 'project')
        self.key = stoneridge.get_config('report', 'key')
        self.secret = stoneridge.get_config('report', 'secret')
        self.archives = stoneridge.get_config('report', 'archives')

        logfile = os.path.join(self.archives, '%s.log' % (int(time.time()),))
        logging.basicConfig(filename=logfile, level=logging.DEBUG,
                format=stoneridge.log_fmt)
        logging.debug('root directory: %s' % (self.rootdir,))
        logging.debug('pattern: %s' % (self.pattern,))
        logging.debug('host: %s' % (self.host,))
        logging.debug('project: %s' % (self.project,))
        logging.debug('oauth key: %s' % (self.key,))
        logging.debug('oauth secret: %s' % (self.secret,))
        logging.debug('archives: %s' % (self.archives,))

    def run(self):
        files = glob.glob(self.pattern)
        logging.debug('files to upload: %s' % (files,))
        for fpath in files:
            logging.debug('reading %s' % (fpath,))
            with file(fpath, 'rb') as f:
                try:
                    dataset = json.load(f)
                    logging.debug('read data: %s' % (dataset,))
                except:
                    # This one is crap, trash it so we never try it again
                    logging.debug('bad json: %s' % (f.read(),))
                    logging.debug('deleting bad data')
                    os.unlink(fpath)
                    continue

            logging.debug('uploading data')
            request = dzclient.DatazillaRequest('https', self.host,
                    self.project, self.key, self.secret)
            response = request.send(dataset)
            logging.debug('got status code %s' % (response.status,))
            if response.status != 200:
                logging.debug('bad status code')
                continue

            result = json.load(response)
            logging.debug('got result %s' % (result,))
            if result['status'] != 'well-formed JSON stored':
                logging.debug('bad status message')
                continue

            # Keep a copy of the data around so we can do archaeology later
            fname = os.path.basename(fpath)
            fdst = os.path.join(self.archives, fname)
            logging.debug('mv %s => %s' % (fpath, fdst))
            shutil.copyfile(fpath, fdst)

            # If we get here, everything went ok, so we can delete the file
            logging.debug('deleting uploaded file')
            os.unlink(fpath)

@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config', required=True)
    args = parser.parse_args()

    stoneridge._conffile = args.config

    reporter = StoneRidgeReporter()
    reporter.run()
