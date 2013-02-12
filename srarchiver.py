#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging
import os
import shutil
import zipfile

import stoneridge


class StoneRidgeArchiver(object):
    """A class to zip up all the results and logging from a stone ridge
    run, and put the results with the stone ridge archvies.
    """
    def run(self):
        logging.debug('archiver running')
        outdir = stoneridge.get_config('run', 'out')
        archivedir = stoneridge.get_config('stoneridge', 'archives')
        srid = stoneridge.get_config('run', 'srid')
        netconfig = stoneridge.get_config('run', 'netconfig')
        infofile = stoneridge.get_config('run', 'info')
        metadata = stoneridge.get_config('run', 'metadata')

        with file(infofile, 'rb') as f:
            info = json.load(f)
            logging.debug('loaded info %s' % (info,))

        arcname = 'stoneridge_%s_%s_%s_%s_%s' % (info['date'],
                                                 info['test_machine']['name'],
                                                 info['test_build']['revision'],
                                                 srid,
                                                 netconfig)
        logging.debug('archive name %s.zip' % (arcname,))


        filename = os.path.join(archivedir, '%s.zip' % (arcname,))
        if not os.path.exists(archivedir):
            logging.debug('making archive directory %s' % (archivedir,))
            os.mkdir(archivedir)

        logging.debug('opening zip file for writing')
        zfile = zipfile.ZipFile(filename, mode='w')

        # Put all the files under a directory in the zip named for the zip
        # file itself, for easy separation when unzipping multiple archives
        # in the same place
        logging.debug('adding files to zip')
        for dirpath, dirs, files in os.walk(outdir):
            dirname = dirpath.replace(outdir, arcname, 1)
            logging.debug('directory %s -> %s' % (dirpath, dirname))
            # Add the directories to the zip
            for d in dirs:
                logging.debug('subdirectory %s' % (d,))
                zfile.write(os.path.join(dirpath, d),
                        arcname=os.path.join(dirname, d))
            # Add the files to the zip
            for f in files:
                logging.debug('file %s' % (f,))
                zfile.write(os.path.join(dirpath, f),
                        arcname=os.path.join(dirname, f))

        logging.debug('closing zip file')
        zfile.close()

        # Make a copy where the uploader will find it
        shutil.copyfile(filename, metadata)


@stoneridge.main
def main():
    parser = stoneridge.TestRunArgumentParser()
    parser.parse_args()

    archiver = StoneRidgeArchiver()
    archiver.run()
