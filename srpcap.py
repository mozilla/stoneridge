#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import base64
import json
import logging
import os
import requests

import stoneridge


class StoneRidgePcap(object):
    def __init__(self, stop):
        self.stop = stop
        self.macaddr = stoneridge.get_config('machine', 'macaddr')
        self.netconfig = stoneridge.get_config('run', 'netconfig')
        self.host = stoneridge.get_config('tcpdump', self.netconfig)
        self.outdir = stoneridge.get_config('run', 'out')
        self.stdout = os.path.join(self.outdir, 'tcpdump.out')
        self.pcap = os.path.join(self.outdir, 'traffic.pcap')

        logging.debug('stop: %s' % (stop,))
        logging.debug('macaddr: %s' % (self.macaddr,))
        logging.debug('netconfig: %s' % (self.netconfig,))
        logging.debug('host: %s' % (self.host,))
        logging.debug('output directory: %s' % (self.outdir,))
        logging.debug('tcpdump output: %s' % (self.stdout,))
        logging.debug('packet capture: %s' % (self.pcap,))

    def start_pcap(self):
        url = 'http://%s/start/%s' % (self.host, self.macaddr)
        response = requests.post(url)
        res = json.loads(response.text)
        if res['status'] != 'ok':
            logging.error('Error starting pcap: %s' % (res['message'],))
        else:
            logging.debug('Started pcap')

    def stop_pcap(self):
        url = 'http://%s/stop/%s' % (self.host, self.macaddr)
        response = requests.post(url)
        res = json.loads(response.text)
        if res['status'] != 'ok':
            logging.error('Error stopping pcap: %s' % (res['message'],))
            return

        url = 'http://%s/retrieve/%s' % (self.host, self.macaddr)
        response = requests.post(url)
        res = json.loads(response.text)
        if res['status'] != 'ok':
            logging.error('Error retrieving pcap: %s' % (res['message'],))
            return

        stdout = base64.b64decode(res['data']['stdout'])
        pcap = base64.b64decode(res['data']['pcap'])

        with file(self.stdout, 'wb') as f:
            f.write(stdout)

        with file(self.pcap, 'wb') as f:
            f.write(pcap)

    def run(self):
        if self.stop:
            self.stop_pcap()
        else:
            self.start_pcap()


@stoneridge.main
def main():
    parser = stoneridge.TestRunArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--start', dest='start', action='store_true')
    group.add_argument('--stop', dest='stop', action='store_true')
    args = parser.parse_args()

    pcap = StoneRidgePcap(args.stop)
    pcap.run()
