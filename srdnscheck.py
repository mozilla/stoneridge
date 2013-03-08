#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging
import socket
import sys

import stoneridge


def send_email():
    myos = stoneridge.get_config('machine', 'os')
    netconfig = stoneridge.get_config('run', 'netconfig')
    srid = stoneridge.get_config('run', 'srid')
    logging.debug('sending email: os=%s, netconfig=%s, srid=%s' %
                  (myos, netconfig, srid))

    to = 'hurley@mozilla.com'
    subject = 'DNS Update Failed'
    msg = '''The DNS Update failed for the following run:
        OS: %s
        Netconfig: %s
        SRID: %s
    ''' % (myos, netconfig, srid)

    stoneridge.mail(to, subject, msg)


def check_private(bits):
    if bits[0] != '172':
        logging.error('IP is not in 172/8')
        send_email()
        sys.exit(1)

    if not (16 <= int(bits[1]) <= 31):
        logging.error('IP is not in 172.16/12')
        send_email()
        sys.exit(1)


def check_public(bits):
    if bits[0] == '172' and (16 <= int(bits[1]) <= 31):
        logging.error('IP is in 172.16/12')
        send_email()
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
        send_email()
        sys.exit(1)

    logging.debug('ip = %s' % (ip,))

    bits = ip.split('.')

    if args.public:
        logging.debug('Checking for a public result')
        check_public(bits)
    else:
        logging.debug('Checking for a private result')
        check_private(bits)
