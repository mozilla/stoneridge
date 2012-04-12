#!/usr/bin/env python

import argparse
import os
import requests

import stoneridge

class StoneRidgeDownloader(object):
    def __init__(self, server, downloaddir, outdir):
        self.server = server
        self.downloaddir = downloaddir
        self.outdir = os.path.abspath(outdir)

    def _download_file(self, filename):
        url = 'http://%s/%s/%s/%s' % (self.server, self.downloaddir,
                stoneridge.download_platform(), filename)
        r = requests.get(url)
        with file(filename) as f:
            f.write(r.text)

    def run(self):
        if not os.path.exists(self.outdir):
            os.path.mkdir(self.outdir)
        os.chdir(self.outdir)

        filename = 'firefox.%s' % (stoneridge.download_suffix(),)
        self._download_file(filename)
        self._download_file('tests.zip')


@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', dest='server', required=True,
                        help='Server to download from')
    parser.add_argument('-d', dest='downloaddir', default='latest',
                        help='Path where files live on server')
    parser.add_argument('-o', dest='outdir', required=True,
                        help='Path to download files to')
    args = parser.parse_args()

    downloader = StoneRidgeDownloader(args.server, args.downloaddir, args.outdir)
    downloader.run()
