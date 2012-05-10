#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
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
    def __init__(self, srconffile, srnetconfig, srroot, srwork, srxpcout):
        """srconffile - .ini file containing stone ridge configuration
        srnetconfig - network configuration for current test
        srroot - installation directory of stone ridge
        srwork - working directory for the current invocation (must exist)
        srxpcout - subdirectory to eventually dump xpcshell output to
        """
        self.srconffile = srconffile
        self.srnetconfig = srnetconfig
        self.srroot = srroot
        self.srwork = srwork
        self.srxpcout = srxpcout
        self.logfile = None
        self.log = None
        self.archive_on_failure = False
        self.cleaner_called = False

    def do_error(self, stage):
        """Print an error and raise an exception that will be handled by the
        top level
        """
        self.log.write('Error exit during %s' % (stage,))
        raise StoneRidgeException('Error running %s: see %s\n' % (stage,
            self.logfile))

    def run_process(self, stage, *args):
        """Run a particular subprocess with the default arguments, as well as
        any arguments requested by the caller while writing status info to the
        log
        """
        script = os.path.join(self.srroot, 'stoneridge_%s.py' % (stage,))

        command = [sys.executable,
                   script,
                   '--config', self.srconffile,
                   '--netconfig', self.srnetconfig,
                   '--root', self.srroot,
                   '--workdir', self.srwork,
                   '--xpcout', self.srxpcout]
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
        stoneridge.setup_dirnames(self.srroot, self.srwork, self.srxpcout)

        for d in (stoneridge.outdir, stoneridge.downloaddir):
            os.mkdir(d)

        for d in (stoneridge.archivedir, stoneridge.logdir):
            if not os.path.exists(d):
                os.mkdir(d)

        self.logfile = os.path.join(stoneridge.logdir,
                'stoneridge_%s.log' % (int(time.time()),))

        with file(self.logfile, 'wb') as f:
            self.log = f

            self.run_process('downloader')

            self.run_process('unpacker')

            self.run_process('info_gatherer')

            self.archive_on_failure = True

            self.run_process('dns_updater')

            self.run_process('runner')

            self.run_process('dns_updater', '--restore')

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
    group = parser.add_mutually_exclusive_group()
    parser.add_argument('--config', dest='config', default='/etc/stoneridge.ini')
    parser.add_argument('--netconfig', dest='netconfig', required=True,
            choices=stoneridge.netconfigs.keys())
    group.add_argument('--no-update', dest='update', default=True,
            action='store_false')
    group.add_argument('--update-only', dest='update_only', default=False,
            action='store_true')
    parser.add_argument('--workdir', dest='workdir')
    args = parser.parse_args()

    if args.update:
        stoneridge.update(args.config)
        if not args.update_only:
            exec_args = [sys.executable, sys.executable, __file__,
                         '--no-update', '--config', args.config]
            if args.workdir:
                exec_args.extend(['--workdir', args.workdir])
            os.execl(*exec_args)

    # Figure out where we live so we know where our root directory is
    srroot = os.path.split(__file__)[0]

    # Create a working space for this run
    if args.workdir:
        srwork = os.path.abspath(args.workdir)
        if not os.path.exists(srwork):
            os.mkdir(srwork)
    else:
        srwork = tempfile.mkdtemp()

    # Make a name for output from xpcshell (can't make the actual directory yet
    # because we don't know what directory it'll live in)
    srxpcout = os.path.basename(tempfile.mktemp())

    cronjob = StoneRidgeCronJob(args.config, args.netconfig, srroot, srwork,
            srxpcout)
    cronjob.run()
