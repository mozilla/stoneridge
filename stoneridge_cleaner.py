#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import os
import shutil

import stoneridge

@stoneridge.main
def main():
    """A simple cleanup program for stone ridge that blows away the working
    directory
    """
    parser = stoneridge.ArgumentParser()
    parser.parse_args()
    shutil.rmtree(stoneridge.workdir)
    if os.path.exists(stoneridge.xpcoutdir):
        shutil.rmtree(stoneridge.xpcoutdir)
