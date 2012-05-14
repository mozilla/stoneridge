#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import glob
import os
import requests

import stoneridge

class StoneRidgeReporter(object):
    def __init__(self):
        self.rootdir = stoneridge.get_config('server', 'directory')
        self.pattern = os.path.join(self.rootdir, '*.json')
        self.url = stoneridge.get_config('report', 'url')

    def run(self):
        files = glob.glob(self.pattern)
        for fpath in files:
            fname = os.path.basename(f)
            unlink_ok = False
            with file(fpath, 'rb') as f:
                try:
                    requests.post(self.url, files={fname: f})
                    unlink_ok = True
                except:
                    pass
            if unlink_ok:
                os.unlink(fpath)

@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config', required=True)
    args = parser.parse_args()

    stoneridge._conffile = args.config

    reporter = StoneRidgeReporter()
    reporter.run()
