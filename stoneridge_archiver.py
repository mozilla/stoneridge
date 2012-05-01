#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import json
import os
import zipfile

import stoneridge

class StoneRidgeArchiver(object):
    """A class to zip up all the results and logging from a stone ridge
    run, and put the results with the stone ridge archvies.
    """
    def run(self):
        with file(os.path.join(stoneridge.outdir, 'info.json'), 'rb') as f:
            info = json.load(f)

        arcname = 'stoneridge_%s_%s_%s_%s' % (info['testrun']['date'],
                                              info['test_machine']['name'],
                                              info['test_build']['revision'],
                                              info['testrun']['suite'])


        filename = os.path.join(stoneridge.archivedir, '%s.zip' % (arcname,))
        zfile = zipfile.ZipFile(filename, mode='wb')

        # Put all the files under a directory in the zip named for the zip
        # file itself, for easy separation when unzipping multiple archives
        # in the same place
        for dirpath, dirs, files in os.walk(stoneridge.outdir):
            dirname = dirpath.replace(stoneridge.outdir, arcname, 1)
            # Add the directories to the zip
            for d in dirs:
                zfile.write(os.path.join(dirpath, d),
                        arcname=os.path.join(dirname, d))
            # Add the files to the zip
            for f in files:
                zfile.write(os.path.join(dirpath, f),
                        arcname=os.path.join(dirname, f))

        zfile.close()

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()

    parser.parse_args()

    archiver = StoneRidgeArchiver()
    archiver.run()
