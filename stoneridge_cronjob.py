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
    """Specially-typed exception to indicate failure while running one of the
    subprograms. This is so we can ignore errors in programs run to handle
    an error condition, so we can see the original error.
    """
    pass

class StoneRidgeCronJob(object):
    """Class that runs as the cron job to run Stone Ridge tests
    """
    def __init__(self, conffile, srroot, srwork):
        """conffile - .ini file containing stone ridge configuration
        srroot - installation directory of stone ridge
        srwork - working directory for the current invocation (must exist)
        """
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

        self.upload_url = cp.get('upload', 'url')

    def do_error(self, stage):
        """Print an error and raise an exception that will be handled by the
        top level
        """
        self.log.write('Error running %s: see %s\n' % (stage, self.logfile))
        raise StoneRidgeException, 'Error exit during %s' % (stage,)

    def run_process(self, stage, *args):
        """Run a particular subprocess with the default arguments, as well as
        any arguments requested by the caller while writing status info to the
        log
        """
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
            # The process failed to run correctly, we need to say so
            self.log.write('### FAILED: %s@%s\n' % (stage, int(time.time())))
            if self.archive_on_failure:
                # We've reached the point in our run where we have something to
                # save off for usage. Archive it, but don't try to archive again
                # if for some reason the archival process fails :)
                self.archive_on_failure = False
                try:
                    self.run_process('archiver')
                except StoneRidgeException, e:
                    pass
            if not self.cleaner_called:
                # Let's be nice and clean up after ourselves
                self.cleaner_called = True
                try:
                    self.run_process('cleaner')
                except StoneRidgeException, e:
                    pass

            # Finally, bubble the error up to the top level
            self.do_error(stage)
        else:
            self.log.write('### SUCCEEDED: %s@%s\n' % (stage, int(time.time())))

    def run(self):
        stoneridge.setup_dirnames(self.srroot, self.srwork)

        for d in (stoneridge.outdir, stoneridge.downloaddir):
            os.mkdir(d)

        for d in (stoneridge.archivedir, stoneridge.logdir):
            if not os.path.exists(d):
                os.mkdir(d)

        self.logfile = os.path.join(stoneridge.logdir,
                'stoneridge_%s.log' % (int(time.time()),))

        with file(self.logfile, 'wb') as f:
            self.log = f

            self.run_process('downloader', '--server', self.dl_server,
                    '--downloaddir', self.dl_rootdir)

            self.run_process('unpacker')

            self.run_process('info_gatherer')

            self.archive_on_failure = True

            self.run_process('runner')

            self.run_process('collator')

            self.run_process('uploader', '--url', self.upload_url)

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
    parser.add_option('--workdir', dest='workdir')
    args = parser.parse_arguments()

    if args['update']:
        stoneridge.update(parser['config']):
        return subprocess.call([sys.executable, sys.executable, __file__,
                '--no-update'])

    # Figure out where we live so we know where our root directory is
    srroot = os.path.split(__file__)[0]

    # Create a working space for this run
    if args['workdir']:
        srwork = os.path.abspath(args['workdir'])
        if not os.path.exists(srwork):
            os.mkdir(srwork)
    else:
        srwork = tempfile.mkdtemp()

    cronjob = StoneRidgeCronJob(args['config'], srroot, srwork)
    cronjob.run()
