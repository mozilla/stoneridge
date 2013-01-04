#!/usr/bin/env python

import argparse
import logging
import subprocess

import stoneridge

class StoneRidgeMaster(stoneridge.QueueListener):
    queue = 'sr_incoming'

    def setup(self):
        self.queues = {
            'broadband':stoneridge.QueueWriter(self.host, 'nc_broadband'),
            'umts':stoneridge.QueueWriter(self.host, 'nc_umts'),
            'gsm':stoneridge.QueueWriter(self.host, 'nc_gsm')
        }

    def handle(self, nightly, ldap, sha, netconfigs):
        if nightly:
            path = 'nightly/latest-mozilla-central'
        else:
            path = 'try-builds/%s-%s' % (ldap, sha)
        logging.debug('Path to builds: %s' % (path,))

        try:
            stoneridge.run_process('srcloner.py', '--path', path,
                    '--config', self.args['config'])
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

            queue.enqueue(operating_systems=operating_systems,
                    nightly=nightly, ldap=ldap, sha=sha)

@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config', required=True)
    parser.add_argument('--host', dest='host', required=True)
    parser.add_argument('--log', dest='log', required=True)
    args = parser.parse_args()

    master = StoneRidgeMaster(args.host, config=args.config)
    master.run()
