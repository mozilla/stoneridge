#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import logging

import stoneridge


class StoneRidgeScheduler(stoneridge.QueueListener):
    def setup(self, rpc_queue, netconfig):
        self.rpc_queue = rpc_queue
        self.netconfig = netconfig

        self.runners = {
            'linux':stoneridge.RpcCaller(self.host, stoneridge.LINUX_QUEUE,
                self.rpc_queue),
            'mac':stoneridge.RpcCaller(self.host, stoneridge.MAC_QUEUE,
                self.rpc_queue),
            'windows':stoneridge.RpcCaller(self.host, stoneridge.WINDOWS_QUEUE,
                self.rpc_queue)
        }

    def handle(self, srid, operating_systems):
        for o in operating_systems:
            runner = self.runners.get(o, None)
            if runner is None:
                logging.error('Invalid operating system: %s' % (o,))
                continue

            logging.debug('Calling to run %s on %s' % (srid, o))
            res = runner(srid=srid, netconfig=self.netconfig)

            if res['ok']:
                logging.debug('Run of %s on %s succeeded' % (srid, o))
            else:
                logging.error('Run of %s on %s failed: %s' % (srid, o,
                    res['msg']))


@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', dest='log', required=True)
    parser.add_argument('--netconfig', dest='netconfig',
            choices=stoneridge.NETCONFIGS.keys(), required=True)
    parser.add_argument('--host', dest='host', required=True)
    args = parser.parse_args()

    queues = stoneridge.NETCONFIG_QUEUES[args.netconfig]

    scheduler = StoneRidgeScheduler(host, queues['incoming'],
            rpc_queue=queues['rpc'], netconfig=args.netconfig)
    scheduler.run()
