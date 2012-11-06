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

nochange = False

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
        p = subprocess.Popen(['networksetup', '-listnetworkserviceorder'],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p.wait()
        lines = p.stdout.readlines()
        mainline = None
        srline = None
        for line in lines:
            if line.startswith('(1)'):
                mainline = line
            elif line.startswith('(2)'):
                srline = line

        self.main_if = mainline.strip().split(' ', 1)[1]
        self.sr_if = srline.strip().split(' ', 1)[1]
        self.dnsbackup = os.path.join(rundir, 'dnsbackup')

    def _set_dns(self, dnsservers):
        args = ['networksetup', '-setdnsservers', self.main_if] + dnsservers
        p = subprocess.Popen(args, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
        p.wait()

    def reset_dns(self):
        orig_dns = None
        if os.path.exists(self.dnsbackup):
            with file(self.dnsbackup) as f:
                orig_dns = [line.strip() for line in f.readlines()]
                orig_dns = [d for d in orig_dns if d] # Filter out empty lines

        if orig_dns:
            if nochange:
                print 'Reset to %s' % (orig_dns,)
            else:
                self._set_dns(orig_dns)

    def set_dns(self, dnsserver):
        if not os.path.exists(self.dnsbackup):
            # Only need to bother saving this once per run
            args = ['networksetup', '-getdnsservers', self.main_if]
            p = subprocess.Popen(args, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT)
            p.wait()

            dns_servers = p.stdout.readlines()
            if dns_servers:
                with file(self.dnsbackup, 'w') as f:
                    f.write(''.join(dns_servers))

        if nochange:
            print 'Set to %s' % (dnsserver,)
        else:
            self._set_dns([dnsserver])

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
        newlines = []
        for line in lines:
            if line.startswith('nameserver '):
                if not replaced:
                    newlines.append(nsline)
                    replaced = True
            else:
                newlines.append(line)

        # If we didn't already have a nameserver line, let's add one now
        if not replaced:
            newlines.append(nsline)

        # And save off the new resolv.conf
        with file(self.resolvconf, 'w') as f:
            f.write('\n'.join(newlines))

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
    parser.add_argument('--nochange', dest='nochange', action='store_true')
    args = parser.parse_args()

    global nochange
    nochange = args.nochange

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
