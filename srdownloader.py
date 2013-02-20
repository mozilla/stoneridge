#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os
import requests

import stoneridge


class StoneRidgeDownloader(object):
    """Downloads the firefox archive and the tests.zip for a the machine this is
    running on and puts them in the stone ridge working directory
    """
    def __init__(self):
        self.server = stoneridge.get_config('download', 'server')
        self.downloadroot = stoneridge.get_config('download', 'root')
        self.download_platform = stoneridge.get_config('machine',
                                                       'download_platform')
        self.download_suffix = stoneridge.get_config('machine',
                                                     'download_suffix')
        self.srid = stoneridge.get_config('run', 'srid')
        self.downloaddir = stoneridge.get_config('run', 'download')
        logging.debug('server = %s' % (self.server,))
        logging.debug('download root = %s' % (self.downloadroot,))
        logging.debug('platform = %s' % (self.download_platform,))
        logging.debug('suffix = %s' % (self.download_suffix,))
        logging.debug('srid = %s' % (self.srid,))
        logging.debug('downloaddir = %s' % (self.downloaddir,))

    def _download_file(self, filename):
        url = 'http://%s/%s/%s/%s/%s' % (self.server, self.downloadroot,
                                         self.srid, self.download_platform,
                                         filename)
        logging.debug('downloading %s from %s' % (filename, url))
        r = requests.get(url)
        if r.status_code != 200:
            msg = 'Error downloading %s: %s' % (filename, r.status_code)
            logging.critical(msg)
            raise Exception(msg)

        with file(filename, 'wb') as f:
            f.write(r.content)

    def run(self):
        logging.debug('downloader running')
        if not os.path.exists(self.downloaddir):
            logging.debug('creating download directory %s' %
                          (self.downloaddir,))
            os.mkdir(self.downloaddir)
        os.chdir(self.downloaddir)

        self._download_file('firefox.%s' % (self.download_suffix,))
        self._download_file('tests.zip')


@stoneridge.main
def main():
    parser = stoneridge.TestRunArgumentParser()
    parser.parse_args()

    downloader = StoneRidgeDownloader()
    downloader.run()
