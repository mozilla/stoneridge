#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import json
import os
import zipfile

import stoneridge

class StoneRidgeArchiver(object):
    def __init__(self):
        pass

    def run(self):
        with file(os.path.join(stoneridge.outdir, 'info.json')) as f:
            info = json.load(f)

        arcname = 'stoneridge_%s_%s_%s_%s' % (info['test_machine']['name'],
                                              info['test_build']['revision'],
                                              info['testrun']['suite'],
                                              info['testrun']['date'])


        filename = os.path.join(stoneridge.archivedir, '%s.zip' % (arcname,))
        zfile = zipfile.ZipFile(filename, mode='w')

        for dirpath, dirs, files in os.walk(stoneridge.outdir):
            dirname = dirpath.replace(stoneridge.outdir, arcname, 1)
            for d in dirs:
                zfile.write(os.path.join(dirpath, d),
                        arcname=os.path.join(dirname, d))
            for f in files:
                zfile.write(os.path.join(dirpath, f),
                        arcname=os.path.join(dirname, f))

        zfile.close()

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()

    parser.parse_arguments()

    archiver = StoneRidgeArchiver()
    archiver.run()
