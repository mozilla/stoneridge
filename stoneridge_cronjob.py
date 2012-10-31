#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import ConfigParser
import cStringIO
import os
import subprocess
import sys
import tempfile
import time

import stoneridge

# Import this last so the configuration changes get picked up
import logging

class StoneRidgeException(Exception):
    """Specially-typed exception to indicate failure while running one of the
    subprograms. This is so we can ignore errors in programs run to handle
    an error condition, so we can see the original error.
    """
    pass

class StoneRidgeCronJob(object):
    """Class that runs as the cron job to run Stone Ridge tests
    """
    def __init__(self, srconffile, srnetconfig, srroot, srwork, srxpcout, log,
                 logdir):
        """srconffile - .ini file containing stone ridge configuration
        srnetconfig - network configuration for current test
        srroot - installation directory of stone ridge
        srwork - working directory for the current invocation (must exist)
        srxpcout - subdirectory to eventually dump xpcshell output to
        log - name of log file
        logdir - directory of log file
        """
        self.srconffile = srconffile
        self.srnetconfig = srnetconfig
        self.srroot = srroot
        self.srwork = srwork
        self.srxpcout = srxpcout
        self.logdir = logdir
        self.logfile = log
        self.archive_on_failure = False
        self.cleaner_called = False
        self.procno = 1

    def do_error(self, stage):
        """Print an error and raise an exception that will be handled by the
        top level
        """
        logging.error('Error exit during %s' % (stage,))
        raise StoneRidgeException('Error running %s: see %s\n' % (stage,
            self.logfile))

    def run_process(self, stage, *args):
        """Run a particular subprocess with the default arguments, as well as
        any arguments requested by the caller
        """
        script = os.path.join(self.srroot, 'stoneridge_%s.py' % (stage,))
        logfile = os.path.join(self.logdir, '%02d_%s.log' % (self.procno, stage))
        self.procno += 1

        command = [sys.executable,
                   script,
                   '--config', self.srconffile,
                   '--netconfig', self.srnetconfig,
                   '--root', self.srroot,
                   '--workdir', self.srwork,
                   '--xpcout', self.srxpcout,
                   '--log', logfile]
        command.extend(args)

        logging.debug('Running %s' % (stage,))
        logging.debug(' '.join(command))

        proc_stdout = cStringIO.StringIO()

        rval = subprocess.call(command, stdout=proc_stdout,
                stderr=subprocess.STDOUT)

        logging.debug(proc_stdout.getvalue())
        proc_stdout.close()

        if rval:
            # The process failed to run correctly, we need to say so
            logging.debug('FAILED: %s' % (stage,))
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
            logging.debug('SUCCEEDED: %s' % (stage,))

    def run(self):
        stoneridge.setup_dirnames(self.srroot, self.srwork, self.srxpcout)

        for d in (stoneridge.outdir, stoneridge.downloaddir):
            os.mkdir(d)

        if not os.path.exists(stoneridge.archivedir):
            os.mkdir(d)

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


@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config', required=True)
    parser.add_argument('--log', dest='log', required=True)
    parser.add_argument('--logdir', dest='logdir', required=True)
    args = parser.parse_args()

    # Figure out where we live so we know where our root directory is
    srroot = os.path.split(os.path.abspath(__file__))[0]

    cp = ConfigParser.ConfigParser()
    cp.read([args.config])
    netconfigs = cp.options('dns')

    for netconfig in netconfigs:
        # Create a working space for this run
        srwork = tempfile.mkdtemp()

        # Make a name for output from xpcshell (can't make the actual directory
        # yet, because we don't know what directory it'll live in)
        srxpcout = os.path.basename(tempfile.mktemp())

        cronjob = StoneRidgeCronJob(args.config, netconfig, srroot, srwork,
                srxpcout, args.log, args.logdir)
        cronjob.run()
