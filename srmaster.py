#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging
import subprocess
import uuid

import stoneridge


class StoneRidgeMaster(stoneridge.QueueListener):
    def setup(self, config):
        self.queues = {
            'broadband': stoneridge.QueueWriter(stoneridge.BROADBAND_QUEUE),
            'umts': stoneridge.QueueWriter(stoneridge.UMTS_QUEUE),
            'gsm': stoneridge.QueueWriter(stoneridge.GSM_QUEUE)
        }
        self.logdir = stoneridge.get_config('stoneridge', 'logs')
        self.config = config

    def handle(self, nightly, ldap, sha, netconfigs, operating_systems):
        srid = str(uuid.uuid4())
        logfile = 'cloner_%s.log' % (srid,)
        cloner_log = os.path.join(self.logdir, logfile)
        args = ['srcloner.py', '--path', path, '--config', self.config,
                '--srid', srid, '--log', cloner_log]
        if nightly:
            path = 'nightly/latest-mozilla-central'
            args.append('--nightly')
        else:
            path = 'try-builds/%s-%s' % (ldap, sha)
        logging.debug('Path to builds: %s' % (path,))

        if 'linux' in operating_systems:
            args.append('--linux')
        if 'mac' in operating_systems:
            args.append('--mac')
        if 'windows' in operating_systems:
            args.append('--windows')

        try:
            stoneridge.run_process(*args)
        except subprocess.CalledProcessError as e:
            # Either we will retry this later, at the cloner's request, or the
            # error has already been logged by run_process and there's no
            # recovery we can do.
            return

        for nc in netconfigs:
            queue = self.queues.get(nc, None)
            if queue is None:
                logging.warning('Got request for invalid netconfig %s' % (nc,))
                continue

            queue.enqueue(operating_systems=operating_systems, srid=srid)


def daemon(config):
    master = StoneRidgeMaster(stoneridge.INCOMING_QUEUE,
            config=config)
    master.run()


@stoneridge.main
def main():
    parser = stoneridge.DaemonArgumentParser()
    args = parser.parse_args()

    parser.start_daemon(daemon, config=args._sr_config_)
