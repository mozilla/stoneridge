#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import glob
import json
import os
import platform
import subprocess
import sys
import time

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
        self.heads = heads
        self.tails = tails

        # Figure out where our builtins live based on where we are
        self.builtin = os.path.dirname(__file__)

    def _build_testlist(self):
        """Return a list of test file names, all relative to the test root.
        This weeds out any tests that may be missing from the directory.
        """
        if not self.tests:
            return [os.path.basename(f) for f in
                    glob.glob(os.path.join(stoneridge.testroot, '*.js'))]

        tests = []
        for candidate in self.tests:
            if not candidate.endswith('.js'):
                sys.stdout.write('### INVALID TEST %s\n' % (candidate,))
            elif not os.path.exists(os.path.join(stoneridge.testroot, candidate)):
                sys.stdout.write('### MISSING TEST %s\n' % (candidate,))
            else:
                tests.append(candidate)

        return tests

    def _build_preargs(self):
        """Build the list of arguments (including head js files) for everything
        except the actual command to run.
        """
        preargs = ['-v', '180', '-f', os.path.join(self.builtin, 'head.js')]

        for head in self.heads:
            abshead = os.path.abspath(head)
            preargs.extend(['-f', abshead])

        return preargs

    def run(self):
        tests = self._build_testlist()
        preargs = self._build_preargs()

        # Ensure our output directory exists
        os.makedirs(stoneridge.xpcoutdir)

        self.outfiles = []
        self.failures = []
        for test in tests:
            outfile = os.path.join(stoneridge.xpcoutdir, '%s.out' % (test,))
            args = preargs + ['-f', os.path.join(stoneridge.testroot, test)] + \
                    ['-e', 'do_stoneridge(' + outfile + '); quit(0);']
            res, _ = stoneridge.run_xpcshell(args, stdout=sys.stdout)
            outfiles.append(outfile)
            if res:
                sys.stdout.write('### TEST FAIL: %s\n' % (test,))
                failures.append(test)


@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    parser.add_argument('--head', dest='heads', action='append', metavar='HEADFILE',
                        help='Extra head.js file to append (can be used more than once)')
    parser.add_argument('tests', nargs='*', metavar='TEST',
                        help='Name of single test file to run')

    args = parser.parse_args()

    runner = StoneRidgeRunner(args.tests, args.heads)
    runner.run()
