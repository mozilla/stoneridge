#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging

import stoneridge


class StoneRidgeScheduler(stoneridge.QueueListener):
    def setup(self, rpc_queue, netconfig):
        self.rpc_queue = rpc_queue
        self.netconfig = netconfig

        self.runners = {
            'linux': stoneridge.RpcCaller(stoneridge.LINUX_QUEUE,
                self.rpc_queue),
            'mac': stoneridge.RpcCaller(stoneridge.MAC_QUEUE,
                self.rpc_queue),
            'windows': stoneridge.RpcCaller(stoneridge.WINDOWS_QUEUE,
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


def daemon(netconfig):
    queues = stoneridge.NETCONFIG_QUEUES[netconfig]

    scheduler = StoneRidgeScheduler(queues['incoming'], rpc_queue=queues['rpc'],
            netconfig=netconfig)
    scheduler.run()


@stoneridge.main
def main():
    parser = stoneridge.DaemonArgumentParser()
    parser.add_argument('--netconfig', dest='netconfig',
            choices=stoneridge.NETCONFIGS.keys(), required=True)
    args = parser.parse_args()

    parser.start_daemon(daemon, netconfig=args.netconfig)
