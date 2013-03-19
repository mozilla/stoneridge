#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os
import platform
import re
import shutil
import SocketServer
import struct

import stoneridge


dnspat = re.compile('^[0-9]+ : ([0-9.]+)$')
rundir = None
nochange = False
winreg = None


class BaseDnsModifier(SocketServer.BaseRequestHandler):
    """A class providing an interface for modifying DNS servers on a platform.
    """
    @staticmethod
    def save_dns():
        logging.critical('Base save_dns called!')
        raise NotImplementedError

    def set_dns(self, server):
        """Set the DNS server on the system to <server>
        """
        logging.critical('Base set_dns called!')
        raise NotImplementedError

    def reset_dns(self):
        """Reset the DNS server on the system to the default
        """
        logging.critical('Base reset_dns called!')
        raise NotImplementedError

    def handle(self):
        """Handles a single connection
        """
        msghdr = self.request.recv(2)
        logging.debug('Handling request. Header: %s' % (msghdr,))
        msgdata = ''
        msgtype, dlen = struct.unpack('cB', msghdr)
        logging.debug('Message type: %s' % (msgtype,))
        logging.debug('Data length: %s' % (dlen,))
        if dlen:
            msgdata = self.request.recv(dlen)
            logging.debug('Received data %s' % (msgdata,))

        status = 'ok'
        if msgtype == 's':
            logging.debug('setting dns')
            self.set_dns(msgdata)
        elif msgtype == 'r':
            logging.debug('resetting dns')
            self.reset_dns()
        else:
            logging.error('Unknown msg type, erroring')
            status = 'no'

        self.request.sendall(status)


class MacDnsModifier(BaseDnsModifier):
    @staticmethod
    def get_main_if():
        p = stoneridge.Process(['networksetup', '-listnetworkserviceorder'])
        stdout, _ = p.communicate()
        lines = stdout.split('\n')
        logging.debug('networksetup -listnetworkserviceorder => %s' % (lines,))
        mainline = None
        for line in lines:
            if line.startswith('(1)'):
                mainline = line
                logging.debug('Main interface line: %s' % (mainline,))
        if mainline is None:
            return None

        return mainline.strip().split(' ', 1)[1]

    @staticmethod
    def get_backup():
        return os.path.join(rundir, 'dnsbackup')

    @staticmethod
    def save_dns():
        dnsbackup = MacDnsModifier.get_backup()
        logging.debug('Backup file: %s' % (dnsbackup,))

        if not os.path.exists(dnsbackup):
            logging.debug('Saving original DNS server(s)')
            main_if = MacDnsModifier.get_main_if()
            if main_if is None:
                logging.critical('Could not figure out main interface!')
                return

            args = ['networksetup', '-getdnsservers', main_if]
            logging.debug('Getting original DNS server(s) using command '
                          'line %s' % (args,))
            p = stoneridge.Process(args)
            stdout, _ = p.communicate()

            dns_servers = stdout.split('\n')
            logging.debug('Got original dns server(s) %s' % (dns_servers,))
            if dns_servers:
                with file(dnsbackup, 'w') as f:
                    logging.debug('Writing backup file')
                    f.write('\n'.join(dns_servers))
            else:
                logging.error('Unable to get dns servers!')

    def setup(self):
        logging.debug('Initializing Mac handler')

        self.main_if = MacDnsModifier.get_main_if()
        self.dnsbackup = MacDnsModifier.get_backup()
        logging.debug('Main interface name: %s' % (self.main_if,))
        logging.debug('Backup file: %s' % (self.dnsbackup,))

    def _set_dns(self, dnsservers):
        args = ['networksetup', '-setdnsservers', self.main_if] + dnsservers
        logging.debug('Setting dns using command line %s' % (args,))
        p = stoneridge.Process(args)
        p.communicate()

    def reset_dns(self):
        orig_dns = None
        if os.path.exists(self.dnsbackup):
            logging.debug('DNS backup file exists')
            with file(self.dnsbackup) as f:
                orig_dns = [line.strip() for line in f.readlines()]
                logging.debug('Stripped lines: %s' % (orig_dns,))
                orig_dns = [d for d in orig_dns if d]  # Filter out empty lines
                logging.debug('Non-empty lines: %s' % (orig_dns,))

        logging.debug('Original DNS server(s): %s' % (orig_dns,))

        if orig_dns:
            if nochange:
                print 'Reset to %s' % (orig_dns,)
            else:
                self._set_dns(orig_dns)

    def set_dns(self, dnsserver):
        logging.debug('New DNS server: %s' % (dnsserver,))

        if nochange:
            print 'Set to %s' % (dnsserver,)
        else:
            self._set_dns([dnsserver])


class LinuxDnsModifier(BaseDnsModifier):
    resolvconf = '/etc/resolv.conf'

    @staticmethod
    def save_dns():
        dnsbackup = LinuxDnsModifier.get_dnsbackup()

        if not os.path.exists(dnsbackup):
            # Save a backup copy of our existing resolv.conf
            logging.debug('Saving original resolv.conf')
            shutil.copyfile(LinuxDnsModifier.resolvconf, dnsbackup)

    @staticmethod
    def get_dnsbackup():
        return os.path.join(rundir, 'resolv.conf')

    def setup(self):
        logging.debug('Initializing linux handler')
        self.dnsbackup = LinuxDnsModifier.get_dnsbackup()
        logging.debug('Existing resolv.conf: %s' % (self.resolvconf,))
        logging.debug('Backup file: %s' % (self.dnsbackup,))

    def reset_dns(self):
        logging.debug('Copying backup file to resolv.conf')
        shutil.copyfile(self.dnsbackup, self.resolvconf)

    def set_dns(self, dnsserver):
        lines = None
        with file(self.resolvconf) as f:
            lines = f.readlines()

        logging.debug('Original resolv.conf lines: %s' % (lines,))

        nsline = 'nameserver %s' % (dnsserver,)
        logging.debug('New nameserver line: %s' % (nsline,))

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
            logging.debug('Was missing nameserver line, adding our own')
            newlines.append(nsline)

        logging.debug('New resolv.conf lines: %s' % (newlines,))

        # And save off the new resolv.conf
        with file(self.resolvconf, 'w') as f:
            logging.debug('Writing resolv.conf')
            f.write('\n'.join(newlines))


class WindowsDnsModifier(BaseDnsModifier):
    @staticmethod
    def save_dns():
        # Windows doesn't actually change DNS servers, so no worries here
        pass

    def setup(self):
        self.key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            'System\\CurrentControLSet\\Services\\TCPIP\\Parameters')

    def reset_dns(self):
        logging.debug('About to kill DNS on StoneRidge interface')
        netsh = stoneridge.Process(['netsh.exe', 'ipv4', 'set', 'dnsservers',
                                    'StoneRidge', 'static', 'none',
                                    'validate=no'])
        netsh.communicate()

        logging.debug('About to resurrect WAN interface')
        netsh = stoneridge.Process(['netsh.exe', 'interface', 'set',
                                    'interface', 'name=WAN', 'admin=ENABLED'])
        netsh.communicate()

        logging.debug('About to reset search suffix')
        winreg.SetValue(self.key, 'SearchList', winreg.REG_SZ, 'mozilla.com')

    def set_dns(self, dnsserver):
        logging.debug('About to kill WAN interface')
        netsh = stoneridge.Process(['netsh.exe', 'interface', 'set',
                                    'interface', 'name=WAN', 'admin=DISABLED'])
        netsh.communicate()

        logging.debug('About to clear search suffix')
        winreg.SetValue(self.key, 'SearchList', winreg.REG_SZ, '')

        logging.debug('About to set DNS on StoneRidge interface')
        netsh = stoneridge.Process(['netsh.exe', 'ipv4', 'set', 'dnsservers',
                                    'StoneRidge', 'static', dnsserver,
                                    'validate=no'])
        netsh.communicate()


def daemon():
    sysname = platform.system()
    if sysname == 'Linux':
        logging.debug('Running on linux, using LinuxDnsModifier')
        DnsModifier = LinuxDnsModifier
    elif sysname == 'Darwin':
        logging.debug('Running on OS X, using MacDnsModifier')
        DnsModifier = MacDnsModifier
    elif sysname == 'Windows':
        logging.debug('Running on Windows, using WindowsDnsModifier')
        DnsModifier = WindowsDnsModifier
        global winreg
        import _winreg
        winreg = _winreg
    else:
        msg = 'Invalid system: %s' % (sysname,)
        logging.critical(msg)
        raise ValueError(msg)

    logging.debug('Saving existing DNS')
    DnsModifier.save_dns()

    logging.debug('Starting server on localhost:63250')
    server = SocketServer.TCPServer(('localhost', 63250), DnsModifier)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


@stoneridge.main
def main():
    parser = stoneridge.DaemonArgumentParser()
    parser.add_argument('--nochange', dest='nochange', action='store_true')
    args = parser.parse_args()

    global nochange
    nochange = args.nochange

    global rundir
    rundir = stoneridge.get_config('stoneridge', 'run')

    parser.start_daemon(daemon)
