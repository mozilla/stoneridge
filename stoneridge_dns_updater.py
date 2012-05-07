#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import ConfigParser

import stoneridge

class DnsModifier(object):
    """A class providing an interface for modifying DNS servers on a platform.
    """
    def __new__(cls):
        """Do some magic to return the proper kind of DNS Modifier when we're
        constructed
        """
        if _platsys in ('Linux', 'Darwin'):
            return UnixDnsModifier()
        return WinDnsModifier()

    def enable_debug(self):
        """Turn on debug mode in the dns modifier process
        """
        raise NotImplementedError

    def set_dns(self, server):
        """Set the DNS server on the system to <server>
        """
        raise NotImplementedError

    def reset_dns(self):
        """Reset the DNS server on the system to the default
        """
        raise NotImplementedError

    def quit(self):
        """Close up shop nicely on the system-level dns modifier process
        """
        raise NotImplementedError

    def terminate(self):
        """Close up shop NOT nicely on the system-level dns modifier process
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

    def enable_debug(self):
        # Not implemented on windows
        pass

    def set_dns(self, dnsserver):
        return self._converse('s', dnsserver)

    def reset_dns(self):
        return self._converse('r')

    def quit(self):
        self.reset_dns()

    def terminate(self):
        self.quit()

class UnixDnsModifier(DnsModifier):
    def __new__(self):
        return object.__new__(UnixDnsModifier)

    def __init__(self):
        args = [necko.SUIDWRAP, sys.executable, 'resolvconf.py']
        self.proc = subprocess.Popen(args, cwd=necko.BINROOT,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)

    def _converse(self, msg):
        self.proc.stdin.write('%s\n' % (msg,))
        self.proc.stdin.flush()
        return self.proc.stdout.readline().strip() == 'ok'

    def enable_debug(self):
        return self._converse('debug yes')

    def set_dns(self, dnsserver):
        return self._converse('set %s' % (dnsserver,))

    def reset_dns(self):
        return self._converse('reset')

    def quit(self):
        self.reset_dns()
        self.proc.stdin.write('quit\n')
        self.proc.stdin.flush()
        self.proc.wait()

    def terminate(self):
        self.reset_dns()
        self.proc.terminate()

class StoneRidgeDnsUpdater(object):
    def __init__(self, restore):
        self.restore = restore
        self.modifier = DnsModifier()

    def run(self):
        if self.restore:
            self.modifier.reset_dns()
            return

        cp = ConfigParser.SafeConfigParser()
        cp.read([stoneridge.conffile])
        try:
            dns_server = cp.get('dns', stoneridge.current_netconfig)
        except (Configparser.NoSectionError, ConfigParser.NoOptionError), e:
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
