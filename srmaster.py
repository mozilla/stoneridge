#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os
import subprocess
import time
import uuid

import stoneridge


class StoneRidgeMaster(stoneridge.QueueListener):
    def setup(self):
        self.queues = {
            'broadband': stoneridge.QueueWriter(
                stoneridge.NETCONFIG_QUEUES['broadband']),
            'umts': stoneridge.QueueWriter(
                stoneridge.NETCONFIG_QUEUES['umts']),
            'gsm': stoneridge.QueueWriter(
                stoneridge.NETCONFIG_QUEUES['gsm'])
        }
        self.logdir = stoneridge.get_config('stoneridge', 'logs')
        self.config = stoneridge.get_config_file()

    def handle(self, nightly, ldap, sha, netconfigs, operating_systems,
               srid=None, attempt=1):
        if srid is None:
            srid = str(uuid.uuid4())

        logging.debug('Got request')
        logging.debug('Nightly: %s' % (nightly,))
        logging.debug('LDAP: %s' % (ldap,))
        logging.debug('SHA: %s' % (sha,))
        logging.debug('Netconfigs: %s' % (' '.join(netconfigs),))
        logging.debug('Operating systems: %s' % (' '.join(operating_systems),))
        logging.debug('Attempt: %s' % (attempt,))
        logging.debug('SRID: %s' % (srid,))

        logfile = 'cloner_%s.log' % (srid,)
        cloner_log = os.path.join(self.logdir, logfile)
        args = ['srcloner.py', '--config', self.config, '--srid', srid,
                '--log', cloner_log, '--attempt', attempt]
        if nightly:
            args.append('--nightly')

            # Make sure the list of netconfigs and operating systems is right
            netconfigs = stoneridge.NETCONFIGS
            operating_systems = stoneridge.OPERATING_SYSTEMS
        else:
            if not ldap or not sha:
                logging.error('Missing ldap/sha for non-nightly build')
                return

            args.extend(['--ldap', ldap])
            args.extend(['--sha', sha])
            for ops in operating_systems:
                args.append('--%s' % (ops,))
            for nc in netconfigs:
                args.append('--%s' % (nc,))

        try:
            stoneridge.run_process(*args)
        except subprocess.CalledProcessError:
            # Either we will retry this later, at the cloner's request, or the
            # error has already been logged by run_process and there's no
            # recovery we can do.
            return

        # In order to have the points for each OS/netconfig match up with each
        # other for a particular test run (good for graphing), we set the
        # timestamp once we know we're going to actually run the test (which is
        # right now, after we've cloned the builds).
        # We also sleep for one second, so we don't accidentally have 2
        # different runs show up at the same time as each other on the graphs.
        # Sure, it's unlikely, but sleeping for a second won't kill us, and
        # better safe than sorry!
        tstamp = int(time.time())
        time.sleep(1)

        for nc in netconfigs:
            queue = self.queues.get(nc, None)
            if queue is None:
                logging.warning('Got request for invalid netconfig %s' % (nc,))
                continue

            queue.enqueue(operating_systems=operating_systems, srid=srid,
                          tstamp=tstamp, ldap=ldap)


def daemon():
    master = StoneRidgeMaster(stoneridge.INCOMING_QUEUE)
    master.run()


@stoneridge.main
def main():
    parser = stoneridge.DaemonArgumentParser()
    parser.parse_args()

    parser.start_daemon(daemon)
