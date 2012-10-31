#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import os
import shutil

import stoneridge

import logging

@stoneridge.main
def main():
    """A simple cleanup program for stone ridge that blows away the working
    directory
    """
    logging.debug('cleaner running')
    parser = stoneridge.ArgumentParser()
    parser.parse_args()
    if stoneridge.workdir and os.path.exists(stoneridge.workdir):
        logging.debug('removing workdir %s' % (stoneridge.workdir,))
        shutil.rmtree(stoneridge.workdir)
    if stoneridge.xpcoutdir and os.path.exists(stoneridge.xpcoutdir):
        logging.debug('removing xpcshell output directory %s' %
                (stoneridge.xpcoutdir,))
        shutil.rmtree(stoneridge.xpcoutdir)
