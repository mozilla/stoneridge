#!/usr/bin/env python

import subprocess
import sys
import time

SRHOME = '/home/stoneridge'
SRPYTHON = '%s/stoneridge' % (SRHOME,)
SRRUN = '%s/srrun.py' % (SRPYTHON,)
SRWORKER = '%s/srworker.py' % (SRPYTHON,)
SRINI = '%s/stoneridge.ini' % (SRHOME,)
LOG = '%s/srworker.log' % (SRHOME,)

cli = [sys.executable, SRRUN, SRWORKER, '--config', SRINI, '--log', LOG]

p = subprocess.Popen(cli)
p.wait()

while True:
    # Sleep indefinitely in case of failure, so we choose when to kill the
    # terminal. This isn't particularly useful on the actual infrastructure,
    # but it works great for debugging errors during testing.
    time.sleep(60)
