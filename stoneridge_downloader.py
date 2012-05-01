#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import os
import human_curl as requests

import stoneridge

class StoneRidgeDownloader(object):
    """Downloads the firefox archive and the tests.zip for a the machine this is
    running on and puts them in the stone ridge working directory
    """
    def __init__(self, server, downloaddir):
        self.server = server
        self.downloaddir = downloaddir

    def _download_file(self, filename):
        url = 'http://%s/%s/%s/%s' % (self.server, self.downloaddir,
                stoneridge.download_platform, filename)
        r = requests.get(url)
        with file(filename, 'wb') as f:
            f.write(r.content)

    def run(self):
        os.chdir(stoneridge.workdir)

        filename = os.path.join(stoneridge.downloaddir,
                'firefox.%s' % (stoneridge.download_suffix),))
        self._download_file(filename)

        filename = os.path.join(stoneridge.downloaddir, 'tests.zip')
        self._download_file('tests.zip')


@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    parser.add_argument('--server', dest='server', required=True,
                        help='Server to download from')
    parser.add_argument('--downloaddir', dest='downloaddir', default='latest',
                        help='Path where files live on server')
    args = parser.parse_args()

    downloader = StoneRidgeDownloader(args.server, args.downloaddir)
    downloader.run()
