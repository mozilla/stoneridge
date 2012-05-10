#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import struct
import socket
import sys

import stoneridge

class StoneRidgeDnsUpdater(object):
    def __init__(self, restore):
        self.restore = restore
        self.peer = ('127.0.0.1', 63250)

    def _converse(self, msgtype, msgdata=None):
        if msgdata is None:
            msgdata = ''

        # Set up our connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(self.peer)

        # First message is type + length of following message
        msghdr = struct.pack('cB', msgtype, len(msgdata))
        sock.send(msghdr)

        # Send the data if we have any
        if msgdata:
            sock.send(msgdata)

        # Get our result and clean up
        result = sock.recv(2)
        sock.close()

        if result != 'ok':
            sys.stderr.write('Error %ssetting dns server\n' %
                    ('re' if msgtype == 'r' else ''))

    def _set_dns(self, dnsserver):
        self._converse('s', dnsserver)

    def _reset_dns(self):
        self._converse('r')

    def run(self):
        if self.restore:
            self._reset_dns()
            return

        dns_server = stoneridge.get_config('dns', stoneridge.current_netconfig)
        if dns_server is None:
            sys.stderr.write('Error finding dns server for config %s\n' %
                    (stoneridge.current_netconfig,))
            return

        self._set_dns(dns_server)

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()

    parser.add_argument('--restore', dest='restore', action='store_true',
            default=False, help='Restore DNS server to default settings')

    args = parser.parse_args()

    dns_updater = StoneRidgeDnsUpdater(args.restore)
    dns_updater.run()
