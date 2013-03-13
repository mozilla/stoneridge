#!/usr/bin/env python

import subprocess
import sys

SRHOME = '/home/hurley/srhome'
SRPYTHON = '%s/stoneridge' % (SRHOME,)
SRRUN = '%s/srrun.py' % (SRPYTHON,)
SRWORKER = '%s/srworker.py' % (SRPYTHON,)
SRINI = '%s/stoneridge.ini' % (SRHOME,)
LOG = '%s/srworker.log' % (SRHOME,)

cli = [sys.executable, SRRUN, SRWORKER, '--config', SRINI, '--log', LOG]
p = subprocess.Popen(['/usr/bin/gnome-terminal', '-t', 'Stone Ridge',
                      '-e', ' '.join(cli)])
p.wait()
