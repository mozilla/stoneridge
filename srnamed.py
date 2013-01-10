import argparse
import daemonize
import logging
import subprocess
import sys
import time
import traceback

from dnsproxy import DnsProxyServer, UdpDnsHandler, DnsProxyException
from replay import configure_logging

import stoneridge


listen_ip = None


class NeckoDnsProxyServer(DnsProxyServer):
    def necko_get_ip(self, client):
        try:
            return self.necko_ips[client]
        except (AttributeError, KeyError):
            iproute = subprocess.Popen(['ip', 'route', 'get', client],
                    stdout=subprocess.PIPE)
            res = iproute.stdout.read()
            iproute.wait()
            bits = res.split()
            ip = None
            for i, bit in enumerate(bits):
                if bit == 'src':
                    ip = bits[i + 1]
                    break
            if ip is None:
                # Hail mary, full of something...
                return '127.0.0.1'
            try:
                self.necko_ips[client] = ip
            except AttributeError:
                self.necko_ips = {}
                self.necko_ips[client] = ip
            return self.necko_ips[client]


class NeckoDnsHandler(UdpDnsHandler):
    def handle(self):
        self.data = self.rfile.read()
        self.transaction_id = self.data[0]
        self.flags = self.data[1]
        self.qa_counts = self.data[4:6]
        self.domain = ''
        operation_code = (ord(self.data[2]) >> 3) & 15
        if operation_code == self.STANDARD_QUERY_OPERATION_CODE:
            self.wire_domain = self.data[12:]
            self.domain = self._domain(self.wire_domain)
        else:
            logging.debug("DNS request with non-zero operation code: %s",
                          operation_code)
        real_ip = self.server.passthrough_filter(self.domain)
        if real_ip:
            message = 'passthrough'
            ip = real_ip
        else:
            message = 'handle'
            ip = self.server.necko_get_ip(self.client_address[0])
            # TODO - make the above work again
            ip = listen_ip
        logging.debug('dnsproxy: %s(%s) -> %s', message, self.domain, ip)
        self.reply(self.get_dns_reply(ip))


def daemon():
    configure_logging('debug', None)
    try:
        with(NeckoDnsProxyServer(False, handler=NeckoDnsHandler)):
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        logging.info('Shutting down.')
    except DnsProxyException, e:
        logging.critical(e)
        sys.exit(1)
    except:
        print traceback.format_exc()
        sys.exit(2)
    sys.exit(0)


@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--listen', dest='listen', required=True)
    parser.add_argument('--pidfile', dest='pidfile', required=True)
    parser.add_argument('--log', dest='log', required=True)
    args = parser.parse_args()

    global listen_ip
    listen_ip = args.listen

    daemonize.start(daemon, args.pidfile, args.log)
