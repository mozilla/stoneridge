import logging
import socket
import sys
import time

from dnsproxy import DnsProxyServer, DnsProxyException

import stoneridge


listen_ip = None
dnssrv = None

IGNORE_HOSTS = (
    'puppet1.private.scl3.mozilla.com.',
)

SR_HOSTS = {
    'stone-ridge-linux1.dmz.scl3.mozilla.com.': '172.17.0.1',
    'stone-ridge-linux2.dmz.scl3.mozilla.com.': '172.18.0.1',
    'stone-ridge-linux3.dmz.scl3.mozilla.com.': '172.19.0.1',
    'stone-ridge-linux4.dmz.scl3.mozilla.com.': '172.16.1.1',
    'stone-ridge-win1.dmz.scl3.mozilla.com.': '172.16.1.2',
    'stone-ridge-mac1.dmz.scl3.mozilla.com.': '172.16.1.3',
}


def srlookup(host):
    logging.debug('srlookup: checking %s' % (host,))
    if host in IGNORE_HOSTS:
        logging.debug('attempting to ignore %s' % (host,))
        try:
            return socket.gethostbyname(host)
        except:
            logging.error('Could not get actual IP for %s' % (host,))
            # This should result in NXDOMAIN
            return None

    if host in SR_HOSTS:
        logging.debug('stone ridge host detected: %s' % (host,))
        return SR_HOSTS[host]

    logging.debug('host not found in our exception lists')

    return dnssrv.server_address[0]


def daemon():
    global dnssrv
    logging.debug('about to start proxy server')
    try:
        with DnsProxyServer(srlookup, listen_ip) as dnssrv:
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
