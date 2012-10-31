#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import os
import subprocess
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('--config', dest='config', required=True)
parser.add_argument('--logdir', dest='logdir', required=True)
args = parser.parse_arguments()

now = int(time.time())
logdir = os.path.join(args.logdir, 'stoneridge_logs_%s' % (now,))
os.makedirs(logdir)
cronjob_log = os.path.join(logdir, '00_cronjob.log')

sys.exit(subprocess.call([sys.executable, '--config', args.config,
                          '--logdir', args.logdir, '--log', cronjob_log])
