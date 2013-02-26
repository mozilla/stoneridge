#!/usr/bin/env python

import subprocess
import sys

prog_args = [sys.executable] + sys.argv[1:]

while True:
    p = subprocess.Popen(prog_args, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    p.communicate()
