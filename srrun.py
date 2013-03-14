#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import copy
import os
import platform
import subprocess
import sys

mypath = os.path.abspath(__file__)
mydir = os.path.split(mypath)[0]
if os.getenv('VIRTUAL_ENV'):
    # If we're running in a virtualenv, then we're doing development, and we
    # want to use the virtualenv's python, no matter what system we're running
    # on, since the virtualenv is the only python guaranteed to have all our
    # required third-party modules installed.
    srpython = sys.executable
elif platform.system().lower() == 'windows':
    # Windows doesn't have any special installation, since python doesn't come
    # on windows by default.
    srpython = sys.executable
elif platform.system().lower() == 'darwin':
    # For Mac, we need to make sure we use the homebrew-installed python,
    # instead of the system one, which is out of date.
    srpython = '/usr/local/bin/python'
else:
    # This should handle linux, where we install our own built python in the
    # srhome directory to ensure we're using a modern-enough python instead of
    # whatever may have been installed with the system (which may or may not
    # be modern enough for our purposes).
    srhome = os.path.join(mydir, '..')
    srhome = os.path.abspath(srhome)
    srbin = os.path.join(srhome, 'bin')
    srpython = os.path.join(srbin, 'python')
srpypath = [mydir, os.path.join(mydir, 'wpr')]

env = copy.copy(os.environ)
env['PYTHONPATH'] = os.pathsep.join(srpypath)

# Set a sane umask for all children
os.umask(022)

sys.exit(subprocess.call([srpython] + sys.argv[1:], env=env))
