#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import dzclient
import glob
import json
import os

import stoneridge

class StoneRidgeReporter(object):
    def __init__(self):
        self.rootdir = stoneridge.get_config('server', 'uploads')
        self.pattern = os.path.join(self.rootdir, '*.json')
        self.host = stoneridge.get_config('report', 'host')
        self.project = stoneridge.get_config('report', 'project')
        self.key = stoneridge.get_config('report', 'key')
        self.secret = stoneridge.get_config('report', 'secret')

    def run(self):
        files = glob.glob(self.pattern)
        for fpath in files:
            with file(fpath, 'rb') as f:
                try:
                    dataset = json.load(f)
                except:
                    # This one is crap, trash it so we never try it again
                    os.unlink(fpath)
                    continue

            request = dzclient.DatazillaRequest(self.host, self.project,
                    self.key, self.secret)
            response = request.send(dataset)
            if response.status != 200:
                continue

            result = json.load(response)
            if result['status'] != 'ok':
                continue

            # If we get here, everything went ok, so we can delete the file
            os.unlink(fpath)

@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config', required=True)
    args = parser.parse_args()

    stoneridge._conffile = args.config

    reporter = StoneRidgeReporter()
    reporter.run()
