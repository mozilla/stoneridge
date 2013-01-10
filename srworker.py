#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import logging
import os
import subprocess
import sys
import tempfile

import stoneridge


class StoneRidgeTestRunner(object):
    pass


class StoneRidgeWorker(stoneridge.RpcHandler):
    def setup(self, config, log):
        self.srconffile = config
        self.srroot = stoneridge.get_config('stoneridge', 'root')
        self.srlogdir = stoneridge.get_config('stoneridge', 'logs')
        self.logfile = log
        logging.debug('srconffile: %s' % (self.srconffile,))
        logging.debug('srroot: %s' % (self.srroot,))
        logging.debug('srlogdir: %s' % (self.srlogdir,))
        logging.debug('logfile: %s' % (self.logfile,))

        self.reset()

    def handle(self, srid, netconfig):
        # Have a logger just for this run
        logdir = 'stoneridge_%s_%s' % (srid, netconfig))
        self.logdir = os.path.join(self.srlogdir, logdir)
        os.makedirs(self.logdir)
        logging.debug('Running test with logs in %s' % (self.logdir,))

        logfile = os.path.join(logdir, '00_worker.log')
        handler = logging.FileHandler(logfile)
        formatter = logging.Formatter(fmt=stoneridge.LOG_FMT)
        handler.setFormatter(formatter)
        self.logger = logging.getLogger(logdir)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(handler)

        # Create a working space for this run
        self.srwork = tempfile.mkdtemp()

        # Make a name for output from xpcshell (can't make the actual directory
        # yet, because we don't know what directory it'll live in)
        self.srxpcout = os.path.basename(tempfile.mktemp())

        self.srnetconfig = netconfig
        self.archive_on_failure = False
        self.cleaner_called = False
        self.procno = 1
        self.childlog = None

        self.logger.debug('srwork: %s' % (self.srwork,))
        self.logger.debug('srxpcout: %s' % (self.srxpcout,))
        self.logger.debug('srnetconfig: %s' % (self.srnetconfig,))
        self.logger.debug('archive on failure: %s' % (self.archive_on_failure,))
        self.logger.debug('cleaner called: %s' % (self.cleaner_called,))
        self.logger.debug('procno: %s' % (self.procno,))
        self.logger.debug('childlog: %s' % (self.childlog,))
        self.logger.debug('logdir: %s' % (self.logdir,))

        try:
            self.run_test()
        except StoneRidgeException as e:
            self.logger.exception(e)

        self.reset()

    def reset(self):
        self.srwork = None
        self.srxpcout = None
        self.srnetconfig = None
        self.archive_on_failure = True
        self.cleaner_called = True
        self.procno = -1
        self.childlog = None
        self.logdir = None
        self.logger = None

    def do_error(self, stage):
        """Print an error and raise an exception that will be handled by the
        top level
        """
        self.logger.error('Error exit during %s' % (stage,))
        raise StoneRidgeException('Error running %s: see %s\n' % (stage,
            self.childlog))

    def run_process(self, stage, *args):
        """Run a particular subprocess with the default arguments, as well as
        any arguments requested by the caller
        """
        script = os.path.join(self.srroot, 'sr%s.py' % (stage,))
        logfile = os.path.join(self.logdir, '%02d_%s_%s.log' %
                (self.procno, stage, self.srnetconfig))
        self.procno += 1

        command = [script,
                   '--config', self.srconffile,
                   '--netconfig', self.srnetconfig,
                   '--root', self.srroot,
                   '--workdir', self.srwork,
                   '--xpcout', self.srxpcout,
                   '--log', logfile]
        command.extend(args)
        try:
            stoneridge.run_process(*command, logger=self.logger)
        except subprocess.CalledProcessError as e:
            # The process failed to run correctly, we need to say so
            self.childlog = logfile

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

    def run_test(self):
        stoneridge.setup_dirnames(self.srroot, self.srwork, self.srxpcout)

        for d in (stoneridge.outdir, stoneridge.downloaddir):
            os.mkdir(d)

        if not os.path.exists(stoneridge.archivedir):
            os.mkdir(stoneridge.archivedir)

        self.run_process('downloader')

        self.run_process('unpacker')

        self.run_process('infogatherer')

        self.archive_on_failure = True

        self.run_process('dnsupdater')

        self.run_process('runner')

        self.run_process('dnsupdater', '--restore')

        self.run_process('collator')

        self.run_process('uploader')

        self.archive_on_failure = False

        self.run_process('archiver')

        self.cleaner_called = True
        self.run_process('cleaner')


@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', dest='log', required=True)
    parser.add_argument('--os', dest='os', required=True,
            choices=stoneridge.CLIENT_QUEUES.keys())
    parser.add_argument('--host', dest='host', required=True)
    parser.add_argument('--config', dest='config', required=True)
    args = parser.parse_args()

    queue = stoneridge.CLIENT_QUEUES[args['os']]

    worker = StoneRidgeWorker(host, queue, config=args.config, log=args.log)
    worker.run()
