#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os
import shutil

import stoneridge


@stoneridge.main
def main():
    """A simple cleanup program for stone ridge that blows away the working
    directory
    """
    parser = stoneridge.TestRunArgumentParser()
    parser.parse_args()

    logging.debug('cleaner running')
    workdir = stoneridge.get_config('run', 'work')
    xpcoutdir = stoneridge.get_xpcshell_output_directory()
    if workdir and os.path.exists(workdir):
        logging.debug('removing workdir %s' % (workdir,))
        shutil.rmtree(workdir)
    if xpcoutdir and os.path.exists(xpcoutdir):
        logging.debug('removing xpcshell output directory %s' %
                (xpcoutdir,))
        shutil.rmtree(xpcoutdir)
