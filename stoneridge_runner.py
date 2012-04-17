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
    """A class to run Stone Ridge tests
    """

    def __init__(self, tests=None, heads=None):
        """tests - a subset of the tests to run
           heads - js files that provide extra functionality
        """
        self.xpcshell = os.path.join(stoneridge.bindir, 'xpcshell')
        if not os.path.exists(self.xpcshell) or not os.path.isfile(self.xpcshell):
            raise Exception, 'xpcshell does not exist in bindir'

        # Figure out where TmpD is for xpcshell, to use as our output
        # directory
        self.tmpdir = self._get_xpcshell_tmp()
        if not self.tmpdir:
            raise Exception, 'Could not determine tempdir'

        # These we just copy over and worry about them later
        self.tests = tests
        self.heads = heads
        self.tails = tails

        # Figure out where our builtins live based on where we are
        self.builtin = os.path.dirname(__file__)

    def _run_xpcshell(args, stdout=subprocess.PIPE):
        """Run xpcshell with the appropriate args
        """
        xpcargs = [self.xpcshell] + args
        proc = subprocess.Popen(xpcargs, stdout=stdout,
                stderr=subprocess.STDOUT, cwd=stoneridge.bindir)
        res = proc.wait()
        return (res, proc.stdout)

    def _get_xpcshell_tmp():
        """Determine the temporary directory as xpcshell thinks of it
        """
        # TODO - make sure this works on windows to create a file in python
        _, stdout = self._run_xpcshell(['-e',
            'dump("SR-TMP-DIR:" + '
            '     Components.classes["@mozilla.org/file/directory_service;1"]'
            '     .getService(Components.interfaces.nsIProperties)'
            '     .get("TmpD", Components.interfaces.nsILocalFile)'
            '     .path + "\n");'
            'quit(0);'])
        for line in stdout:
            if line.startswith('SR-TMP-DIR:'):
                return line.strip().split(':', 1)[1]

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
        """Run the tests we've been told to run
        """
        tests = self._build_testlist()
        preargs = self._build_preargs()

        self.outfiles = []
        self.failures = []
        for test in tests:
            outfile = os.path.join(self.tmpdir, '%s.out' % (test,))
            args = preargs + ['-f', os.path.join(stoneridge.testroot, test)] + \
                    ['-e', 'do_stoneridge(' + outfile + '); quit(0);']
            res, _ = self._run_xpcshell(args, stdout=sys.stdout)
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
