#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# run xpcshell -v 180 -f /path/to/head.js -f /path/to/test.js -e 'stoneRidge(<outfile>); quit(0);'
# cwd must be objdir/dist/bin

import argparse
import json
import subprocess
import sys

def run(bindir, root, tests=None, heads=None, tails=None, graphserver=None,
        log=None):
    print 'HEY, I IS RUNNING!'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', dest='bindir', required=True,
                        help='Directory holding xpcshell binary')
    parser.add_argument('-r', dest='root', required=True,
                        help='Root path to test files')
    parser.add_argument('-f', dest='heads', action='append', metavar='HEADFILE',
                        help='Extra head.js file to append (can be used more than once)')
    parser.add_argument('-t', dest='tails', action='append', metavar='TAILFILE',
                        help='Extra tail.js file to append (can be used more than once)')
    parser.add_argument('-g', dest='graphserver',
                        help='URL to post graph info to')
    parser.add_argument('-l', dest='log', help='File to log output to')
    parser.add_argument('tests', nargs='*', metavar='TEST',
                        help='Name of single test file to run')

    args = parser.parse_args()

    run(args.bindir, args.root, args.tests, args.heads, args.tails,
        args.graphserver, args.log)

    sys.exit(0)
