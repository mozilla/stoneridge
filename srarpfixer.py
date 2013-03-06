#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging

import stoneridge


@stoneridge.main
def main():
    parser = stoneridge.TestRunArgumentParser()
    parser.parse_args()

    netconfig = stoneridge.get_config('run', 'netconfig')
    server = stoneridge.get_config('dns', netconfig)
    myos = stoneridge.get_config('machine', 'os')
    logging.debug('netconfig: %s' % (netconfig,))
    logging.debug('server: %s' % (server,))
    logging.debug('os: %s' % (myos,))

    if myos == 'windows':
        countarg = '-n'
    else:
        countarg = '-c'
    logging.debug('countarg: %s' % (countarg,))

    logging.debug('Give me a ping, Vasili. One ping only, please.')
    p = stoneridge.Process(['ping', countarg, '1', server])
    p.communicate()
    p.wait()
