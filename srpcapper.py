#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import base64
import bottle
import json
import logging
import os
import shutil
import tempfile

import stoneridge


class PcapAlreadyRunning(Exception):
    """Special exception type to handle the case when we've been requested to
    start a pcap for a particular machine, but we've already started it and
    it's either waiting to be stopped or waiting to be retrieved.
    """
    pass


class PcapAlreadyStopped(Exception):
    """Special exception type to handle the case when we've been requested to
    stop a pcap for a particular machine, but we've already stopped it and
    it's still waiting around to be retrieved.
    """
    pass


class StoneRidgePcapper(object):
    """This class keeps track of all the pcaps that we're running, and is
    responsible for starting, stopping, and getting the results of those
    processes. It also enforces the "one pcap per host" rule we have going
    on.
    """
    def __init__(self):
        self.pcaps = {}
        self.macaddr = stoneridge.get_config('machine', 'macaddr')
        self.tcpdump = stoneridge.get_config('tcpdump', 'exe')
        self.interface = stoneridge.get_config('tcpdump', 'interface')

    def retrieve(self, macaddr):
        """Get the results from the pcap for <macaddr>
        """
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

        # Be nice, clean up after ourself
        shutil.rmtree(self.pcaps[macaddr]['outdir'])

        # This marks us as no longer running a PCAP for <macaddr>
        del self.pcaps[macaddr]

        # Return everything base64-encoded, so it's json friendly
        return {'stdout': base64.b64encode(stdout),
                'pcap': base64.b64encode(pcap)}

    def stop(self, macaddr):
        """Stop the running pcap for <macaddr>
        """
        if macaddr is None:
            raise Exception('Missing MAC address for PCAP')

        if macaddr not in self.pcaps:
            raise Exception('Not running a PCAP for %s' % (macaddr,))

        if self.pcaps[macaddr]['process'] is None:
            raise PcapAlreadyStopped('PCAP for %s already stopped' %
                                     (macaddr,))

        # Kill the process, and mark it as done
        p = self.pcaps[macaddr]['process']
        self.pcaps[macaddr]['process'] = None
        p.terminate()
        p.wait()

        # Make sure the output from tcpdump is saved to disk
        self.pcaps[macaddr]['stdout_fd'].close()
        self.pcaps[macaddr]['stdout_fd'] = None

    def start(self, macaddr):
        """Start a pcap for traffic between us and <macaddr>
        """
        if macaddr is None:
            raise Exception('Missing MAC address for PCAP')

        if macaddr in self.pcaps:
            raise PcapAlreadyRunning('Already running PCAP for %s' %
                                     (macaddr,))

        self.pcaps[macaddr] = {}

        # Set up all the output files we're going to need, and open our stdout
        # file, so the Process object can funnel stdout to it.
        outdir = tempfile.mkdtemp()
        stdout_filename = os.path.join(outdir, 'tcpdump.out')
        pcap_filename = os.path.join(outdir, 'tcpdump.pcap')
        stdout_fd = file(stdout_filename, 'wb')

        # Start the pcap process
        p = stoneridge.Process([self.tcpdump,
                                '-i', self.interface,
                                '-s', '2000',
                                '-w', pcap_filename,
                                '-U',
                                'ether', 'host', macaddr,
                                'and',
                                'ether', 'host', self.macaddr],
                               stdout=stdout_fd)

        # Save off all the metadata about this process so we can get at it
        # later.
        self.pcaps[macaddr]['outdir'] = outdir
        self.pcaps[macaddr]['stdout_fd'] = stdout_fd
        self.pcaps[macaddr]['stdout'] = stdout_filename
        self.pcaps[macaddr]['pcap'] = pcap_filename
        self.pcaps[macaddr]['process'] = p


# This is our one and only StoneRidgePcapper object, initialized just before
# the web server starts.
pcapper = None


def error(msg):
    """Create an error response with a message and return it.
    """
    logging.debug('Returning error: %s' % (msg,))
    res = {'status': 'error', 'message': msg}
    return json.dumps(res)


def ok(data=None):
    """Create a success response, with optional data to go along with it.
    The data may be a string (message), or another object that is json
    serializable (for example, a dict of stdout and pcap from a process).
    """
    logging.debug('Returning ok')
    res = {'status': 'ok', 'data': data}
    return json.dumps(res)


@bottle.post('/retrieve/:macaddr')
def retrieve(macaddr=None):
    """Web endpoint for getting the results of a pcap process.
    """
    try:
        data = pcapper.retrieve(macaddr)
    except Exception as e:
        logging.exception('Error trying to retrieve for %s' % (macaddr,))
        return error(str(e))

    return ok(data)


@bottle.post('/stop/:macaddr')
def stop(macaddr=None):
    """Web endpoint for stopping a pcap process.
    """
    try:
        pcapper.stop(macaddr)
    except PcapAlreadyStopped as e:
        logging.warning('PCAP already stopped')
        return ok(str(e))
    except Exception as e:
        logging.exception('Error trying to stop for %s' % (macaddr,))
        return error(str(e))

    return ok()


@bottle.post('/start/:macaddr')
def start(macaddr=None):
    """Web endpoint for starting a pcap process.
    """
    try:
        pcapper.start(macaddr)
    except PcapAlreadyRunning as e:
        logging.warning('PCAP already running')
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
