#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging
import socket
import sys

import stoneridge


def send_email(check):
    """Send an email to me so I know when the dns update failed.
    """
    myos = stoneridge.get_config('machine', 'os')
    netconfig = stoneridge.get_config('run', 'netconfig')
    srid = stoneridge.get_config('run', 'srid')
    logging.debug('sending email: os=%s, netconfig=%s, srid=%s, check=%s' %
                  (myos, netconfig, srid, check))

    to = 'hurley@mozilla.com'
    subject = 'DNS Update Failed'
    msg = '''The DNS Update failed for the following run:
        OS: %s
        Netconfig: %s
        SRID: %s
        Check failed: %s
    ''' % (myos, netconfig, srid, check)

    stoneridge.mail(to, subject, msg)


def in_private(ip):
    """Determine if an IP is in our private (172.16/12) network.
    """
    bits = map(int, ip.split('.'))
    return (bits[0] == 172 and (16 <= bits[1] <= 31))


def check_private(ip):
    """Check to make sure the host name resolved to an IP in our private
    stone ridge network.
    """
    if not in_private(ip):
        logging.error('IP is not in 172.16/12')
        send_email('private')
        sys.exit(1)


def check_public(ip):
    """Check to make sure the host name resolved to an IP on the public
    internet.
    """
    if in_private(ip):
        logging.error('IP is in 172.16/12')
        send_email('public')
        sys.exit(1)


@stoneridge.main
def main():
    parser = stoneridge.TestRunArgumentParser()
    parser.add_argument('--public', dest='public', action='store_true')
    args = parser.parse_args()

    logging.debug('Checking dns for example.com')
    try:
        ip = socket.gethostbyname('example.com')
    except:
        logging.exception('Error retrieving IP')
        send_email('gethostbyname')
        sys.exit(1)

    logging.debug('ip = %s' % (ip,))

    if args.public:
        logging.debug('Checking for a public result')
        check_public(ip)
    else:
        logging.debug('Checking for a private result')
        check_private(ip)
