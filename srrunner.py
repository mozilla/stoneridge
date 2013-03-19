#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import glob
import logging
import os

import stoneridge


class StoneRidgeRunner(object):
    """Does the actual work of running the stone ridge xpcshell tests
    """
    def __init__(self, tests=None, heads=None):
        """tests - a subset of the tests to run
        heads - js files that provide extra functionality
        """
        # These we just copy over and worry about them later
        self.tests = tests
        self.heads = heads if heads else []
        logging.debug('requested tests: %s' % (tests,))
        logging.debug('heads: %s' % (heads,))

        self.testroot = stoneridge.get_config('stoneridge', 'testroot')
        self.unittest = stoneridge.get_config_bool('stoneridge', 'unittest')

        logging.debug('testroot: %s' % (self.testroot,))
        logging.debug('unittest: %s' % (self.unittest,))

    def _build_testlist(self):
        """Return a list of test file names, all relative to the test root.
        This weeds out any tests that may be missing from the directory.
        """
        if not self.tests:
            logging.debug('searching for all tests in %s' %
                          (self.testroot,))
            if stoneridge.get_config('test', 'enabled'):
                tests = []
                if os.path.exists(os.path.join(self.testroot, 'fake.js')):
                    tests.append('fake.js')
            else:
                jstests = [os.path.basename(f) for f in
                           glob.glob(os.path.join(self.testroot, '*.js'))]
                try:
                    jstests.remove('fake.js')
                except ValueError:
                    # Don't care if fake.js isn't in the list
                    pass
                pagetests = [os.path.basename(f) for f in
                             glob.glob(os.path.join(self.testroot, '*.page'))]
                tests = jstests + pagetests
            logging.debug('tests found %s' % (tests,))
            return tests

        tests = []
        for candidate in self.tests:
            logging.debug('candidate test %s' % (candidate,))
            if not candidate.endswith('.js'):
                logging.error('invalid test filename %s' % (candidate,))
            elif not os.path.exists(os.path.join(self.testroot, candidate)):
                logging.error('missing test %s' % (candidate,))
            else:
                logging.debug('valid test file %s' % (candidate,))
                tests.append(candidate)

        logging.debug('tests selected %s' % (tests,))
        return tests

    def _build_preargs(self):
        """Build the list of arguments (including head js files) for everything
        except the actual command to run.
        """
        preargs = ['-v', '180']

        for head in self.heads:
            abshead = os.path.abspath(head)
            preargs.extend(['-f', abshead])

        logging.debug('calculated preargs %s' % (preargs,))
        return preargs

    def run(self):
        logging.debug('runner running')
        tests = self._build_testlist()
        preargs = self._build_preargs()
        logging.debug('tests to run: %s' % (tests,))
        logging.debug('args to prepend: %s' % (preargs,))

        # Ensure our output directory exists
        outdir = stoneridge.get_config('run', 'out')
        installroot = stoneridge.get_config('stoneridge', 'root')

        for test in tests:
            logging.debug('test: %s' % (test,))
            outfile = os.path.join(outdir, '%s.out' % (test,))
            logging.debug('outfile: %s' % (outfile,))
            if test.endswith('.js'):
                escaped_outfile = outfile.replace('\\', '\\\\')
                args = preargs + [
                    '-e', 'const _SR_OUT_FILE = "%s";' % (escaped_outfile,),
                    '-f', os.path.join(installroot, 'srdata.js'),
                    '-f', os.path.join(installroot, 'head.js'),
                    '-f', os.path.join(self.testroot, test),
                    '-e', 'do_stoneridge(); quit(0);'
                ]
                logging.debug('xpcshell args: %s' % (args,))
                runner = stoneridge.run_xpcshell
            else:
                args = [
                    '-sr', os.path.join(self.testroot, test),
                    '-sroutput', outfile,
                    # -srwidth, <some width value>,
                    # -srheight, <some height value>,
                    # -srtimeout, <some timeout value per page>,
                    # -srdelay, <some delay value between pages>,
                    # -srmozafterpaint
                ]
                runner = stoneridge.run_firefox

            if self.unittest:
                logging.debug('Not running processes: in unit test mode')
            else:
                process_out_file = '%s.process.out' % (test,)
                process_out_file = os.path.join(outdir, process_out_file)
                logging.debug('process output at %s' % (process_out_file,))
                timed_out = False
                with file(process_out_file, 'wb') as f:
                    try:
                        res = runner(args, f)
                    except stoneridge.TestProcessTimeout:
                        logging.exception('test process timed out!')
                        timed_out = True
                        res = None
                if res or timed_out:
                    logging.error('TEST FAILED: %s' % (test,))
                else:
                    logging.debug('test succeeded')


@stoneridge.main
def main():
    parser = stoneridge.TestRunArgumentParser()
    parser.add_argument('--head', dest='heads', action='append',
                        metavar='HEADFILE',
                        help='Extra head.js file to append (can be used more '
                             'than once)')
    parser.add_argument('tests', nargs='*', metavar='TEST',
                        help='Name of single test file to run')

    args = parser.parse_args()

    runner = StoneRidgeRunner(args.tests, args.heads)
    runner.run()
