#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging

import stoneridge


class StoneRidgeScheduler(stoneridge.QueueListener):
    def setup(self, netconfig):
        self.netconfig = netconfig

        self.runners = {
            'linux': stoneridge.QueueWriter(stoneridge.CLIENT_QUEUES['linux']),
            'mac': stoneridge.QueueWriter(stoneridge.CLIENT_QUEUES['mac']),
            'windows': stoneridge.QueueWriter(stoneridge.CLIENT_QUEUES['windows']),
        }

    def handle(self, srid, operating_systems, tstamp, ldap):
        for o in operating_systems:
            runner = self.runners.get(o, None)
            if runner is None:
                logging.error('Invalid operating system: %s' % (o,))
                continue

            logging.debug('Calling to run %s on %s' % (srid, o))
            runner.enqueue(srid=srid, netconfig=self.netconfig, tstamp=tstamp,
                           ldap=ldap)


def daemon(netconfig):
    scheduler = StoneRidgeScheduler(stoneridge.NETCONFIG_QUEUES[netconfig],
            netconfig=netconfig)
    scheduler.run()


@stoneridge.main
def main():
    parser = stoneridge.DaemonArgumentParser()
    parser.add_argument('--netconfig', dest='netconfig',
            choices=stoneridge.NETCONFIGS, required=True)
    args = parser.parse_args()

    parser.start_daemon(daemon, netconfig=args.netconfig)
