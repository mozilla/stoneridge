#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# run xpcshell -v 180 -f /path/to/head.js -f /path/to/test.js -e 'do_stoneridge(<outfile>); quit(0);'
# cwd must be objdir/dist/bin

import argparse
import glob
import json
import os
import platform
import subprocess
import sys
import time

class StoneRidgeRunner(object):
    """A class to run Stone Ridge tests
    """

    def __init__(self, bindir, root, tests=None, heads=None, graphserver=None,
                 log=None):
        """bindir - the directory where xpcshell lives
           root - the directory where the tests live
           tests - a subset of the tests to run
           heads - js files that provide extra functionality
           graphserver - URL of the graphserver to upload to
           log - file to write debugging output to (stdout by default)
        """
        # Make sure we have a directory with tests
        if not os.path.exists(root) or not os.path.isdir(root):
            raise Exception, 'test root %s is not a directory' % (root,)
        self.testroot = root

        # Make sure xpcshell is where we think it should be
        if not os.path.exists(bindir) or not os.path.isdir(bindir):
            raise Exception, 'bindir %s is not a directory' % (bindir,)
        self.bindir = bindir

        self.xpcshell = os.path.join(self.bindir, 'xpcshell')
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
        self.graphserver = graphserver
        self.log = log

        # Figure out where our builtins live based on where we are
        self.builtin = os.path.dirname(__file__)

    def _run_xpcshell(args, stdout=subprocess.PIPE):
        """Run xpcshell with the appropriate args
        """
        xpcargs = [self.xpcshell] + args
        proc = subprocess.Popen(xpcargs, stdout=stdout,
                stderr=subprocess.STDOUT, cwd=self.bindir)
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
                    glob.glob(os.path.join(self.root, '*.js'))]

        tests = []
        for candidate in self.tests:
            if not candidate.endswith('.js'):
                self.debug.write('### INVALID TEST %s\n' % (candidate,))
            elif not os.path.exists(os.path.join(self.root, candidate)):
                self.debug.write('### MISSING TEST %s\n' % (candidate,))
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

        if self.log:
            xpcshell_out = file(self.log, 'w')
        else:
            xpcshell_out = sys.stdout

        self.outfiles = []
        self.failures = []
        for test in tests:
            outfile = os.path.join(self.tmpdir, '%s.out' % (test,))
            args = preargs + ['-f', os.path.join(self.root, test)] + \
                    ['-e', 'do_stoneridge(' + outfile + '); quit(0);']
            res, _ = self._run_xpcshell(args, stdout=xpcshell_out)
            outfiles.append(outfile)
            if res:
                if self.log:
                    xpcshell_out.write('### TEST FAIL: %s\n' % (test,))
                failures.append(test)

        if self.log:
            xpcshell_out.close()

@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', dest='bindir', required=True,
                        help='Directory holding xpcshell binary')
    parser.add_argument('-r', dest='root', required=True,
                        help='Root path to test files')
    parser.add_argument('-f', dest='heads', action='append', metavar='HEADFILE',
                        help='Extra head.js file to append (can be used more than once)')
    parser.add_argument('tests', nargs='*', metavar='TEST',
                        help='Name of single test file to run')

    args = parser.parse_args()

    runner = StoneRidgeRunner(args.bindir, args.root, args.tests, args.heads)
    runner.run()
