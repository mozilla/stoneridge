#!/usr/bin/env python

import argparse
import logging
import subprocess
import uuid

import stoneridge

class StoneRidgeMaster(stoneridge.QueueListener):
    queue = stoneridge.INCOMING_QUEUE

    def setup(self):
        self.queues = {
            'broadband':stoneridge.QueueWriter(self.host,
                stoneridge.BROADBAND_QUEUE),
            'umts':stoneridge.QueueWriter(self.host, stoneridge.UMTS_QUEUE),
            'gsm':stoneridge.QueueWriter(self.host, stoneridge.GSM_QUEUE)
        }

    def handle(self, nightly, ldap, sha, netconfigs):
        srid = str(uuid.uuid4())
        args = ['srcloner.py', '--path', path, '--config', self.args['config'],
                '--srid', srid]
        if nightly:
            path = 'nightly/latest-mozilla-central'
            args.append('--nightly')
        else:
            path = 'try-builds/%s-%s' % (ldap, sha)
        logging.debug('Path to builds: %s' % (path,))

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

            queue.enqueue(operating_systems=operating_systems,
                    nightly=nightly, ldap=ldap, sha=sha, srid=srid)

@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config', required=True)
    parser.add_argument('--host', dest='host', required=True)
    parser.add_argument('--log', dest='log', required=True)
    args = parser.parse_args()

    master = StoneRidgeMaster(args.host, config=args.config)
    master.run()
