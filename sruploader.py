#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import base64
import glob
import json
import logging
import os

import stoneridge


class StoneRidgeUploader(object):
    """Takes the upload files created by the collator and uploads them to the
    graph server
    """
    def __init__(self):
        self.queue = stoneridge.QueueWriter(stoneridge.OUTGOING_QUEUE)

    def run(self):
        logging.debug('uploader running')

        outdir = stoneridge.get_config('run', 'out')
        pattern = os.path.join(outdir, 'upload_*.json')
        files = glob.glob(pattern)
        if not files:
            # Nothing to do, so forget it!
            logging.debug('no file to upload')
            return

        results = {}
        for filename in files:
            fname = os.path.basename(filename)
            with file(filename) as f:
                results[fname] = json.load(f)

        metadata_file = stoneridge.get_config('run', 'metadata')
        if os.path.exists(metadata_file):
            with file(metadata_file, 'rb') as f:
                contents = f.read()
            metadata = base64.b64encode(contents)
        else:
            # Missing metadata, but we can still report results
            logging.warning('missing metadata, continuing anyway')
            metadata = base64.b64encode('')

        srid = stoneridge.get_config('run', 'srid')
        netconfig = stoneridge.get_config('run', 'netconfig')
        ldap = stoneridge.get_config('run', 'ldap')
        operating_system = stoneridge.get_config('machine', 'os')
        self.queue.enqueue(srid=srid, results=results, metadata=metadata,
                           netconfig=netconfig,
                           operating_system=operating_system,
                           ldap=ldap)


@stoneridge.main
def main():
    parser = stoneridge.TestRunArgumentParser()
    parser.parse_args()

    uploader = StoneRidgeUploader()
    uploader.run()
