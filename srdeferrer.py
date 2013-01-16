#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import sys
import time

import stoneridge


class StoneRidgeDeferrer(object):
    def __init__(self, srid, nightly, ldap, sha, netconfigs, operating_systems,
            attempt):
        self.srid = srid
        self.nightly = nightly
        self.ldap = ldap
        self.sha = sha
        self.netconfigs = netconfigs
        self.operating_systems = operating_systems
        self.attempt = attempt
        self.interval = stoneridge.get_config_int('cloner', 'interval')

    def run(self):
        start = int(time.time())
        end = start + self.interval
        now = start

        while now < end:
            # Sleep for short periods in an attempt to not get too skewed
            time.sleep(30)
            now = int(time.time())

        stoneridge.enqueue(srid=self.srid, nightly=self.nightly, ldap=self.ldap,
                sha=self.sha, netconfigs=self.netconfigs,
                operating_systems=self.operating_systems,
                attempt=self.attempt)


def daemon(deferrer, args):
    deferrer.run()
    os.unlink(args.pidfile)
    sys.exit(0)


@stoneridge.main
def main():
    parser = stoneridge.DaemonArgumentParser()

    parser.add_argument('--srid', dest='srid', required=True)
    parser.add_argument('--attempt', dest='attempt', type=int, required=True)
    parser.add_argument('--nightly', dest='nightly', action='store_true',
            default=False)
    parser.add_argument('--ldap', dest='ldap', default='')
    parser.add_argument('--sha', dest='sha', default='')
    for nc in stoneridge.NETCONFIGS:
        parser.add_argument('--%s' % (nc,), dest='netconfigs',
                action='append_const', const=nc)
    for ops in stoneridge.OPERATING_SYSTEMS:
        parser.add_argument('--%s' % (nc,), dest='operating_systems',
                action='append_const', const=ops)

    args = parser.parse_args()

    deferrer = StoneRidgeDeferrer(args.srid, args.nightly, args.ldap, args.sha,
            args.netconfigs, args.operating_systems, args.attempt,
            args.interval)

    parser.start_daemon(daemon, deferrer=deferrer, args=args)
