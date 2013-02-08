#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import copy
import os
import subprocess
import sys

mypath = os.path.abspath(__file__)
mydir = os.path.split(mypath)[0]
srhome = os.path.join(mydir, '..')
srhome = os.path.abspath(srhome)
srbin = os.path.join(srhome, 'bin')
srpython = os.path.join(srbin, 'python')
srpypath = [mydir, os.path.join(mydir, 'wpr')]

env = copy.copy(os.environ)
env['PYTHONPATH'] = ':'.join(srpypath)

# Set a sane umask for all children
os.umask(022)

sys.exit(subprocess.call([srpython] + sys.argv[1:], env=env))
