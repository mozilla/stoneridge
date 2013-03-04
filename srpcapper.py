#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import base64
import bottle
import json
import logging
import os
import tempfile

import stoneridge


class PcapAlreadyRunning(Exception):
    pass


class PcapAlreadyStopped(Exception):
    pass


class StoneRidgePcapper(object):
    def __init__(self):
        self.pcaps = {}
        self.macaddr = stoneridge.get_config('machine', 'macaddr')
        self.tcpdump = stoneridge.get_config('tcpdump', 'exe')
        self.interface = stoneridge.get_config('tcpdump', 'interface')

    def retrieve(self, macaddr):
        if macaddr is None:
            raise Exception('Missing MAC address for PCAP')

        if macaddr not in self.pcaps:
            raise Exception('Not running a PCAP for %s' % (macaddr,))

        if self.pcaps[macaddr]['process'] is not None:
            raise Exception('PCAP for %s still running' % (macaddr,))

        with file(self.pcaps[macaddr]['stdout']) as f:
            stdout = f.read()

        with file(self.pcaps[macaddr]['pcap']) as f:
            pcap = f.read()

        del self.pcaps[macaddr]

        return {'stdout': base64.b64encode(stdout),
                'pcap': base64.b64encode(pcap)}

    def stop(self, macaddr):
        if macaddr is None:
            raise Exception('Missing MAC address for PCAP')

        if macaddr not in self.pcaps:
            raise Exception('Not running a PCAP for %s' % (macaddr,))

        if self.pcaps[macaddr]['process'] is None:
            raise PcapAlreadyStopped('PCAP for %s already stopped' %
                                     (macaddr,))

        p = self.pcaps[macaddr]['process']
        self.pcaps[macaddr]['process'] = None
        p.terminate()
        p.wait()

        self.pcaps[macaddr]['stdout_fd'].close()
        self.pcaps[macaddr]['stdout_fd'] = None

    def start(self, macaddr):
        if macaddr is None:
            raise Exception('Missing MAC address for PCAP')

        if macaddr in self.pcaps:
            raise PcapAlreadyRunning('Already running PCAP for %s' %
                                     (macaddr,))

        self.pcaps[macaddr] = {}

        outdir = tempfile.mkdtemp()
        stdout_filename = os.path.join(outdir, 'tcpdump.out')
        pcap_filename = os.path.join(outdir, 'tcpdump.pcap')
        stdout_fd = file(stdout_filename, 'wb')

        p = stoneridge.Process([self.tcpdump,
                                '-i', self.interface,
                                '-s', '2000',
                                '-w', pcap_filename,
                                '-U',
                                'ether', 'host', macaddr,
                                'and',
                                'ether', 'host', self.macaddr],
                               stdout=stdout_fd)

        self.pcaps[macaddr]['stdout_fd'] = stdout_fd
        self.pcaps[macaddr]['stdout'] = stdout_filename
        self.pcaps[macaddr]['pcap'] = pcap_filename
        self.pcaps[macaddr]['process'] = p


pcapper = None


def error(msg):
    res = {'status': 'error', 'message': msg}
    return json.dumps(res)


def ok(data=None):
    res = {'status': 'ok', 'data': data}
    return json.dumps(res)


@bottle.post('/retrieve/:macaddr')
def retrieve(macaddr=None):
    try:
        data = pcapper.retrieve(macaddr)
    except Exception as e:
        logging.exception('Error trying to retrieve for %s' % (macaddr,))
        return error(str(e))

    return ok(data)


@bottle.post('/stop/:macaddr')
def stop(macaddr=None):
    try:
        pcapper.stop(macaddr)
    except PcapAlreadyStopped as e:
        return ok(str(e))
    except Exception as e:
        logging.exception('Error trying to stop for %s' % (macaddr,))
        return error(str(e))

    return ok()


@bottle.post('/start/:macaddr')
def start(macaddr=None):
    try:
        pcapper.start(macaddr)
    except PcapAlreadyRunning as e:
        return ok(str(e))
    except Exception as e:
        logging.exception('Error trying to start for %s' % (macaddr,))
        return error(str(e))

    return ok()


def daemon():
    global pcapper

    pcapper = StoneRidgePcapper()
    stoneridge.StreamLogger.bottle_inject()
    bottle.run(host='0.0.0.0', port=7227)


@stoneridge.main
def main():
    parser = stoneridge.DaemonArgumentParser()
    parser.parse_args()

    parser.start_daemon(daemon)
