#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import glob
import os
import requests

import stoneridge

class StoneRidgeUploader(object):
    """Takes the upload files created by the collator and uploads them to the
    graph server
    """
    def __init__(self):
        self.url = stoneridge.get_config('upload', 'url')

    def run(self):
        file_pattern = os.path.join(stoneridge.outdir, 'upload_*.json')
        upload_files = glob.glob(file_pattern)
        files = {os.path.basename(fname): open(fname, 'rb')
                 for fname in upload_files}
        requests.post(self.url, files=files)
        for f in files.values():
            f.close()

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    args = parser.parse_args()

    uploader = StoneRidgeUploader()
    uploader.run()
