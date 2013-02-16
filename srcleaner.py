#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os
import shutil
import sys
import time

import stoneridge


class StoneRidgeCleaner(object):
    def __init__(self):
        self.workdir = stoneridge.get_config('stoneridge', 'work')
        self.keep = stoneridge.get_config('cleaner', 'keep')

    def run(self):
        logging.debug('cleaner running')

        with stoneridge.cwd(self.workdir):
            while True:
                listing = os.listdir('.')
                logging.debug('candidate files: %s' % (listing,))

                directories = [l for l in listing
                               if os.path.isdir(l) and not l.startswith('.')]
                logging.debug('directories: %s' % (directories,))

                times = [(d, os.stat(d).st_mtime) for d in directories]
                times.sort(key=lambda x: x[1])

                delete_us = times[:-self.keep]
                logging.debug('directories to delete: %s' % (delete_us,))

                for d in delete_us:
                    logging.debug('removing %s' % (d,))
                    shutil.rmtree(d)

                # Check again in a minute
                time.sleep(60)


def daemon(args):
    cleaner = StoneRidgeCleaner()
    cleaner.run()
    os.unlink(args.pidfile)
    sys.exit(0)


@stoneridge.main
def main():
    """A simple cleanup program for stone ridge that blows away the working
    directory
    """
    parser = stoneridge.DaemonArgumentParser()
    args = parser.parse_args()
    parser.start_daemon(daemon, args=args)
