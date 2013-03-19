#!/usr/bin/env python

import subprocess

SRWRAPPER = '/home/hurley/srhome/stoneridge/linux/user/srwrapper.py'

p = subprocess.Popen(['/usr/bin/gnome-terminal', '-t', 'Stone Ridge',
                      '-e', SRWRAPPER])
p.wait()
