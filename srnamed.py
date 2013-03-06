import logging
import socket
import sys
import time

from dnsproxy import DnsProxyServer, UdpDnsHandler, DnsProxyException

import stoneridge


listen_ip = None


IGNORE_HOSTS = (
    'puppet1.private.scl3.mozilla.com',
)

SR_HOSTS = {
    'stone-ridge-linux1.dmz.scl3.mozilla.com': '172.17.0.1',
    'stone-ridge-linux2.dmz.scl3.mozilla.com': '172.18.0.1',
    'stone-ridge-linux3.dmz.scl3.mozilla.com': '172.19.0.1',
    'stone-ridge-linux4.dmz.scl3.mozilla.com': '172.16.1.1',
    'stone-ridge-win1.dmz.scl3.mozilla.com': '172.16.1.2',
    'stone-ridge-mac1.dmz.scl3.mozilla.com': '172.16.1.3',
}


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
            ip = listen_ip
        logging.debug('dnsproxy: %s(%s) -> %s', message, self.domain, ip)
        self.reply(self.get_dns_reply(ip))


def necko_passthrough(host):
    logging.debug('passthrough: checking %s' % (host,))
    if host in IGNORE_HOSTS:
        logging.debug('attempting to ignore %s' % (host,))
        try:
            return socket.gethostbyname(host)
        except:
            logging.error('Could not get actual IP for %s, faking it!' %
                          (host,))

    if host in SR_HOSTS:
        logging.debug('stone ridge host detected: %s' % (host,))
        return SR_HOSTS[host]

    logging.debug('host not found in our exception lists')
    return None


def daemon():
    logging.debug('about to start proxy server')
    try:
        with(DnsProxyServer(False, handler=NeckoDnsHandler,
                            passthrough_filter=necko_passthrough)):
            logging.debug('proxy server started')
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        logging.info('Shutting down.')
    except DnsProxyException:
        logging.exception('DNS Proxy Exception')
        sys.exit(1)
    except:
        logging.exception('Unexpected exception')
        sys.exit(2)
    sys.exit(0)


@stoneridge.main
def main():
    parser = stoneridge.DaemonArgumentParser()
    parser.add_argument('--listen', dest='listen', required=True)
    args = parser.parse_args()

    global listen_ip
    listen_ip = args.listen

    parser.start_daemon(daemon)
