#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import base64
import logging
import os

import stoneridge

class StoneRidgeUploader(object):
    """Takes the upload files created by the collator and uploads them to the
    graph server
    """
    def __init__(self, host):
        self.queue = stoneridge.QueueWriter(host, stoneridge.OUTGOING_QUEUE)

    def run(self):
        logging.debug('uploader running')

        if not os.path.exists(stoneridge.results_file):
            # Nothing to do, so forget it!
            logging.debug('no file to upload')
            return

        with file(stoneridge.upload_file) as f:
            results = f.read()

        if os.path.exists(stoneridge.metadata_file):
            with file(stoneridge.metadata_file) as f:
                contents = f.read()
            metadata = base64.b64encode(contents)
        else:
            # Missing metadata, but we can still report results
            logging.warning('missing metadata, continuing anyway')
            metadata = base64.b64encode('')

        self.queue.enqueue(srid=stoneridge.srid, results=results,
                metadata=metadata)

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    parser.add_argument('--host', dest='host', required=True)
    args = parser.parse_args()

    uploader = StoneRidgeUploader(args.host)
    uploader.run()
