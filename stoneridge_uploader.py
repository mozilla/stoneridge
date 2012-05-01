#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import glob
import os
import human_curl as requests

import stoneridge

class StoneRidgeUploader(object):
    """Takes the upload files created by the collator and uploads them to the
    graph server
    """
    def __init__(self, url):
        self.url = url

    def run(self):
        file_pattern = os.path.join(stoneridge.outdir, 'upload_*.json')
        upload_files = glob.glob(file_pattern)
        for upload in upload_files:
            fname = os.path.basename(upload)
            with file(upload, 'rb') as f:
                requests.post(self.url, files=((fname, f),))

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    parser.add_option('--url', dest='url', required=True,
            help='URL of graph server to upload to')
    args = parser.parse_args()

    uploader = StoneRidgeUploader(args.url)
    uploader.run()
