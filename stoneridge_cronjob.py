#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import ConfigParser
import os
import subprocess
import sys
import tempfile
import time

import stoneridge

class StoneRidgeException(Exception):
    pass

class StoneRidgeCronJob(object):
    def __init__(self, conffile, srroot, srwork):
        self.srroot = srroot
        self.srwork = srwork
        self.logfile = None
        self.log = None
        self.archive_on_failure = False
        self.cleaner_called = False

        cp = ConfigParser.SafeConfigParser()
        cp.read([conffile])
        self.dl_server = cp.get('download', 'server')
        self.dl_rootdir = cp.get('download', 'root')

    def do_error(self, stage):
        self.log.write('Error running %s: see %s\n' % (stage, self.logfile))
        raise StoneRidgeException, 'Error exit during %s' % (stage,)

    def run_process(self, stage, *args):
        script = os.path.join(self.srroot, 'stoneridge_%s.py' % (stage,))

        command = [sys.executable,
                   script,
                   '--root', self.srroot,
                   '--workdir', self.srwork]
        command.extend(args)

        self.log.write('### Running %s@%s\n' % (stage, int(time.time())))
        self.log.write('   %s\n' % (' '.join(command),))

        rval = subprocess.call(command, stdout=self.log,
                stderr=subprocess.STDOUT)

        if rval:
            self.log.write('### FAILED: %s@%s\n' % (stage, int(time.time())))
            if self.archive_on_failure:
                self.archive_on_failure = False
                try:
                    self.run_process('archiver')
                except StoneRidgeException, e:
                    pass
            if not self.cleaner_called:
                self.cleaner_called = True
                try:
                    self.run_process('cleaner')
                except StoneRidgeException, e:
                    pass
            self.do_error(stage)
        else:
            self.log.write('### SUCCEEDED: %s@%s\n' % (stage, int(time.time())))

    def run(self):
        stoneridge.ArgumentParser.setup_dirnames(self.srroot, self.srwork)

        for d in (stoneridge.outdir, stoneridge.downloaddir):
            os.mkdir(d)

        for d in (stoneridge.archivedir, stoneridge.logdir):
            if not os.path.exists(d):
                os.mkdir(d)

        self.logfile = os.path.join(stoneridge.logdir,
                'stoneridge_%s.log' % (int(time.time()),))

        with file(self.logfile, 'w') as f:
            self.log = f

            self.run_process('downloader', '--server', self.dl_server,
                    '--downloaddir', self.dl_rootdir)

            self.run_process('unpacker')

            self.run_process('info_gatherer')

            self.archive_on_failure = True

            self.run_process('runner')

            self.run_process('collator')

            self.run_process('uploader')

            self.archive_on_failure = False

            self.run_process('archiver')

            self.cleaner_called = True
            self.run_process('cleaner')

            self.log = None


@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_option('--config', dest='config', default='/etc/stoneridge.ini')
    parser.add_option('--no-update', dest='update', default=True,
            action='store_false')
    args = parser.parse_arguments()

    if args['update']:
        stoneridge.update(parser['config']):
        return subprocess.call([sys.executable, sys.executable, __file__,
                '--no-update'])

    srroot = os.path.split(__file__)[0]
    srwork = tempfile.mkdtemp()

    cronjob = StoneRidgeCronJob(args['config'], srroot, srwork)
    cronjob.run()
