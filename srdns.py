#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import daemonize
import os
import platform
import re
import shutil
import SocketServer
import struct
import subprocess
import sys
import tempfile

import stoneridge

dnspat = re.compile('^[0-9]+ : ([0-9.]+)$')

rundir = tempfile.mkdtemp()

class BaseDnsModifier(SocketServer.BaseRequestHandler):
    """A class providing an interface for modifying DNS servers on a platform.
    """
    def set_dns(self, server):
        """Set the DNS server on the system to <server>
        """
        raise NotImplementedError

    def reset_dns(self):
        """Reset the DNS server on the system to the default
        """
        raise NotImplementedError

    def handle(self):
        """Handles a single connection
        """
        msghdr = self.request.recv(2)
        msgdata = ''
        msgtype, dlen = struct.unpack('cB', msghdr)
        if dlen:
            msgdata = self.request.recv(dlen)

        status = 'ok'
        if msgtype == 's':
            self.set_dns(msgdata)
        elif msgtype == 'r':
            self.reset_dns()
        else:
            status = 'no'

        self.request.sendall(status)

class MacDnsModifier(BaseDnsModifier):
    def setup(self):
        self.dnskey = None
        out = self._scutil('show State:/Network/Global/IPv4').split('\n')
        for line in out:
            line = line.strip()
            if line.startswith('PrimaryService'):
                bits = [x.strip() for x in line.split(':')]
                uuid = bits[1]
                self.dnskey = 'State:/Network/Service/%s/DNS' % (uuid,)
                break

        if self.dnskey is None:
            raise ValueError('Could not determine DNS key')

        self.dnsbackup = os.path.join(rundir, 'dnsbackup')

    def _scutil(self, cmd):
        p = subprocess.Popen(['scutil'], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return p.communicate(cmd)[0]

    def _set_dns(self, dnsserver):
        command = 'd.init\nd.add ServerAddresses * %s\nset %s' % \
                (dnsserver, self.dnskey)
        self._scutil(command)

    def reset_dns(self):
        orig_dns = None
        if os.path.exists(self.dnsbackup):
            with file(self.dnsbackup) as f:
                orig_dns = f.read().strip()

        if orig_dns is not None:
            self._set_dns(orig_dns)

    def set_dns(self, dnsserver):
        # Save the current primary dns server
        orig_dns = []
        out = self._scutil('show %s' % (self.dnskey,)).split('\n')
        for line in out:
            line = line.strip()
            match = dnspat.match(line)
            if match:
                orig_dns.append(match.groups()[0])

        if orig_dns:
            with file(self.dnsbackup, 'w') as f:
                f.write('%s\n' % (' '.join(orig_dns),))

        # Now set the primary dns server to our new one
        self._set_dns(dnsserver)

class LinuxDnsModifier(BaseDnsModifier):
    def setup(self):
        self.resolvconf = '/etc/resolv.conf'
        self.dnsbackup = os.path.join(rundir, 'resolv.conf')

    def reset_dns(self):
        shutil.copyfile(self.dnsbackup, self.resolvconf)

    def set_dns(self, dnsserver):
        # Save a backup copy of our existing resolv.conf
        shutil.copyfile(self.resolvconf, self.dnsbackup)

        lines = None
        with file(self.resolvconf) as f:
            lines = f.readlines()

        nsline = 'nameserver %s' % (dnsserver,)

        # Go through and find the first nameserver line, and replace
        # it with our modified one
        replaced = False
        for i, line in enumerate(lines):
            if line.startswith('nameserver '):
                lines[i] = nsline
                replaced = True
                break

        # If we didn't already have a nameserver line, let's add one now
        if not replaced:
            lines.append(nsline)

        # And save off the new resolv.conf
        with file(self.resolvconf, 'w') as f:
            f.write('\n'.join(lines))

def daemon():
    sysname = platform.system()
    if sysname == 'Linux':
        DnsModifier = LinuxDnsModifier
    elif sysname == 'Darwin':
        DnsModifier = MacDnsModifier
    else:
        raise ValueError('Invalid system: %s' % (sysname,))

    server = SocketServer.TCPServer(('localhost', 63250), DnsModifier)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    shutil.rmtree(rundir)

def do_exit(parser, msg):
    parser.print_usage()
    parser.exit(2, msg % (parser.prog,))

def do_mutex_exit(parser, arg):
    msg = '%%s: error: argument %s: not allowed with argument --nodaemon\n'
    do_exit(parser, msg % (arg,))

def do_missing_exit(parser, arg):
    msg = '%%s: error: argument %s is required\n'
    do_exit(parser, msg % (arg,))

@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pidfile', dest='pidfile')
    parser.add_argument('--log', dest='log')
    parser.add_argument('--nodaemon', dest='nodaemon', action='store_true')
    args = parser.parse_args()

    if args.nodaemon:
        if args.pidfile:
            do_mutex_exit(parser, '--pidfile')
        if args.log:
            do_mutex_exit(parser, '--log')
        daemon()
        sys.exit(0)

    if not args.pidfile:
        do_missing_exit(parser, '--pidfile')
    if not args.log:
        do_missing_exit(parser, '--log')

    daemonize.start(daemon, args.pidfile, args.log)
