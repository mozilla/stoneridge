#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import os
import shutil
import struct
import socket
import subprocess
import sys

import stoneridge

class DnsModifier(object):
    """A class providing an interface for modifying DNS servers on a platform.
    """
    def __new__(cls):
        """Do some magic to return the proper kind of DNS Modifier when we're
        constructed
        """
        if stoneridge.os_name == 'linux':
            return LinuxDnsModifier()

        if stoneridge.os_name == 'mac':
            return MacDnsModifier()

        if stoneridge.os_name == 'windows':
            return WinDnsModifier()

        raise ValueError('Invalid system: %s' % (stoneridge.os_name,))

    def set_dns(self, server):
        """Set the DNS server on the system to <server>
        """
        raise NotImplementedError

    def reset_dns(self):
        """Reset the DNS server on the system to the default
        """
        raise NotImplementedError

class WinDnsModifier(DnsModifier):
    def __new__(self):
        return object.__new__(WinDnsModifier)

    def __init__(self):
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

        return result == 'ok'

    def set_dns(self, dnsserver):
        return self._converse('s', dnsserver)

    def reset_dns(self):
        return self._converse('r')

class MacDnsModifier(DnsModifier):
    def __new__(self):
        return object.__new__(MacDnsModifier)

    def __init__(self):
        self.dnskey = None
        out = self._scutil('show State:/Network/Global/IPv4')
        for line in out:
            if line.strip().startswith('PrimaryService'):
                uuid = line.strip().split(':')[1].strip()
                self.dnskey = 'State:/Network/Service/%s/DNS' % (uuid,)
                break

        if self.dnskey is None:
            raise ValueError('Could not determine DNS key')

        self.dnsbackup = os.path.join(stoneridge.workdir, 'dnsbackup')

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
        orig_dns = None
        out = self._scutil('show %s' % (self.dnskey,))
        for line in out:
            if line.strip().startswith('0'):
                orig_dns = line.strip().split(':')[1].strip()
                break

        if orig_dns is not None:
            with file(self.dnsbackup, 'w') as f:
                f.write('%s\n' % (orig_dns,))

        # Now set the primary dns server to our new one
        self._set_dns(dnsserver)

class LinuxDnsModifier(DnsModifier):
    def __new__(self):
        return object.__new__(LinuxDnsModifier)

    def __init__(self):
        self.resolvconf = '/etc/resolv.conf'
        self.dnsbackup = os.path.join(stoneridge.workdir, 'resolv.conf')

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

class StoneRidgeDnsUpdater(object):
    def __init__(self, restore):
        self.restore = restore
        self.modifier = DnsModifier()

    def run(self):
        if self.restore:
            self.modifier.reset_dns()
            return

        dns_server = stoneridge.get_config('dns', stoneridge.current_netconfig)
        if dns_server is None:
            sys.stderr.write('Error setting dns server for config %s\n' %
                    (stoneridge.current_netconfig,))
            return

        self.modifier.set_dns(dnsserver)

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()

    parser.add_argument('--restore', dest='restore', action='store_true',
            default=False, help='Restore DNS server to default settings')

    args = parser.parse_arguments()

    dns_updater = StoneRidgeDnsUpdater(args.restore)
    dns_updater.run()
