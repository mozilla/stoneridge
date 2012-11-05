#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import glob
import os
import requests

import stoneridge

import logging

class StoneRidgeUploader(object):
    """Takes the upload files created by the collator and uploads them to the
    graph server
    """
    def __init__(self):
        self.url = stoneridge.get_config('upload', 'url')
        logging.debug('upload url: %s' % (self.url,))

    def run(self):
        logging.debug('uploader running')
        file_pattern = os.path.join(stoneridge.outdir, 'upload_*.json')
        upload_files = glob.glob(file_pattern)
        logging.debug('files to upload: %s' % (upload_files,))
        if not upload_files:
            # Nothing to do, so forget it!
            return
        files = {os.path.basename(fname): open(fname, 'rb')
                 for fname in upload_files}
        logging.debug('uploading files')
        requests.post(self.url, files=files)
        logging.debug('closing file handles')
        for f in files.values():
            f.close()

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    args = parser.parse_args()

    uploader = StoneRidgeUploader()
    uploader.run()
