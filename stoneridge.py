# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import ConfigParser
import copy
import inspect
import logging
import os
import platform
import subprocess
import sys
import traceback

import pika

# Network configurations we have available. Map internal/parameter name
# to descriptive name
netconfigs = {
    'broadband':'Modern Wired Broadband (Cable/ADSL)',
    'umts':'Modern Cellular (UMTS)',
    'gsm':'Legacy Cellular (GSM/EDGE)',
}

# General information common to all stoneridge programs
os_name = None
os_version = None
download_platform = None
download_suffix = None
current_netconfig = None
buildid_suffix = None

# Paths that multiple programs need to know about
installroot = None
workdir = None
downloaddir = None
bindir = None
testroot = None
outdir = None
archivedir = None
xpcoutdir = None
xpcoutleaf = None

# Misc configuration
_xpcshell_tmp_dir = None
_conffile = None
_cp = None
_xpcshell_environ = None

# RabbitMQ queue names
INCOMING_QUEUE = 'sr_incoming'
OUTGOING_QUEUE = 'sr_outgoing'

NETCONFIG_QUEUES = {
    'broadband': {'incoming': 'sr_nc_broadband', 'rpc': 'sr_nc_broadband_rpc'},
    'umts': {'incoming': 'sr_nc_umts', 'rpc': 'sr_nc_umts_rpc'},
    'gsm': {'incoming': 'sr_nc_gsm', 'rpc': 'sr_nc_gsm_rpc'}
}

CLIENT_QUEUES = {
    'linux': 'sr_ct_linux',
    'mac': 'sr_ct_mac',
    'windows': 'sr_ct_windows'
}

# Logging configuration
LOG_FMT = '%(asctime)s %(pathname)s:%(lineno)d %(levelname)s: %(message)s'
_parser = argparse.ArgumentParser()
_parser.add_argument('--log')
_args, _ = _parser.parse_known_args()
if _args.log:
    _logger = logging.getLogger()
    _logger.setLevel(logging.DEBUG)
    _handler = logging.FileHandler(_args.log)
    _formatter = logging.Formatter(fmt=LOG_FMT)
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)

def log(msg):
    if _args.log:
        logging.debug(msg)

def log_exc(msg):
    if _args.log:
        logging.exception(msg)

def main(_main):
    """Mark a function as the main function to run when run as a script.
    If that function throws an exception, we'll print the traceback to
    stderr and exit.
    """
    parent = inspect.stack()[1][0]
    name = parent.f_locals.get('__name__', None)
    if name == '__main__':
        log('%s' % (' '.join(sys.argv),))
        try:
            _main()
        except Exception, e:
            log_exc('EXCEPTION')
            traceback.print_exception(type(e), e, sys.exc_info()[2], None,
                    sys.stderr)
            sys.exit(1)
        log('FINISHED')
        sys.exit(0)
    return _main

def get_config(section, option, default=None):
    """Read a config entry from the stoneridge.ini file
    """
    global _cp

    logging.debug('reading %s.%s (default %s)' %  (section, option, default))

    if _cp is None:
        logging.debug('loading config file %s' % (_conffile,))
        _cp = ConfigParser.SafeConfigParser()
        _cp.read([_conffile])

    try:
        val = _cp.get(section, option)
        logging.debug('found %s.%s, returning %s' % (section, option, val))
        return val
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), e:
        logging.debug('unable to find %s.%s, returning default %s' %
                (section, option, default))
        return default

def run_xpcshell(args, stdout=subprocess.PIPE):
    """Run xpcshell with the appropriate args
    """
    global _xpcshell_environ
    if _xpcshell_environ is None:
        _xpcshell_environ = copy.copy(os.environ)
        ldlibpath = _xpcshell_environ.get('LD_LIBRARY_PATH')
        if ldlibpath:
            ldlibpath = os.path.pathsep.join([bindir, ldlibpath])
        else:
            ldlibpath = bindir
        _xpcshell_environ['LD_LIBRARY_PATH'] = ldlibpath

    xpcargs = [xpcshell] + args
    proc = subprocess.Popen(xpcargs, stdout=stdout,
            stderr=subprocess.STDOUT, cwd=bindir,
            env=_xpcshell_environ)
    res = proc.wait()
    return (res, proc.stdout)

def _get_xpcshell_tmp():
    """Determine the temporary directory as xpcshell thinks of it
    """
    global _xpcshell_tmp_dir

    if _xpcshell_tmp_dir is None:
        # TODO - make sure this works on windows to create a file in python
        _, stdout = run_xpcshell(['-e',
            'dump("SR-TMP-DIR:" + '
            '     Components.classes["@mozilla.org/file/directory_service;1"]'
            '     .getService(Components.interfaces.nsIProperties)'
            '     .get("TmpD", Components.interfaces.nsILocalFile)'
            '     .path + "\\n");'
            'quit(0);'])

        for line in stdout:
            if line.startswith('SR-TMP-DIR:'):
                _xpcshell_tmp_dir = line.strip().split(':', 1)[1]

    return _xpcshell_tmp_dir

def get_xpcshell_bin():
    """Return the name of the xpcshell binary
    """
    if os_name == 'windows':
        return 'xpcshell.exe'
    return 'xpcshell'

def _determine_os_name():
    """Determine the os from platform.system
    """
    global os_name
    os_name = platform.system().lower()
    if os_name == 'darwin':
        os_name = 'mac'
    logging.debug('sr os_name: %s' % (os_name,))

def _determine_os_version():
    """Determine the os version
    """
    global os_version
    if os_name == 'linux':
        os_version = ' '.join(platform.linux_distribution()[0:2])
    elif os_name == 'mac':
        os_version = platform.mac_ver()[0]
    elif os_name == 'windows':
        os_version = platform.win32_ver()[1]
    else:
        os_version = 'Unknown'
    logging.debug('sr os_version: %s' % (os_version,))

def _determine_download_platform():
    """Determine which platform to download files for
    """
    global download_platform
    if os_name == 'linux':
        if platform.machine() == 'x86_64':
            download_platform = 'linux64'
        else:
            download_platform = 'linux32'
    elif os_name == 'windows':
        if platform.machine() == 'x86_64':
            download_platform = 'win64'
        else:
            download_platform = 'win32'
    else:
        download_platform = os_name
    logging.debug('sr download_platform: %s' % (download_platform,))

def _determine_download_suffix():
    """Determine the suffix of the firefox archive to download
    """
    global download_suffix
    if os_name == 'linux':
        download_suffix = 'tar.bz2'
    elif os_name == 'mac':
        download_suffix = 'dmg'
    else:
        download_suffix = 'zip'
    logging.debug('sr download_suffix: %s' % (download_suffix,))

def _determine_bindir():
    """Determine the location of the firefox binary based on platform
    """
    global bindir
    if os_name == 'mac':
        bindir = os.path.join(workdir, 'FirefoxNightly.app', 'Contents',
                'MacOS')
    else:
        bindir = os.path.join(workdir, 'firefox')
    logging.debug('sr bindir: %s' % (bindir,))

def setup_dirnames(srroot, srwork, srxpcout):
    """Determine the directory names and platform information to be used
    by this run of stone ridge
    """
    global installroot
    global workdir
    global downloaddir
    global testroot
    global outdir
    global archivedir
    global xpcshell
    global xpcoutdir
    global xpcoutleaf

    installroot = os.path.abspath(srroot)
    workdir = os.path.abspath(srwork)
    downloaddir = os.path.join(workdir, 'dl')
    testroot = os.path.join(installroot, 'tests')
    outdir = os.path.join(workdir, 'out')
    archivedir = os.path.join(installroot, 'archives')
    logging.debug('sr installroot: %s' % (srroot,))
    logging.debug('sr workdir: %s' % (workdir,))
    logging.debug('sr downloaddir: %s' % (downloaddir,))
    logging.debug('sr testroot: %s' % (testroot,))
    logging.debug('sr outdir: %s' % (outdir,))
    logging.debug('sr archivedir: %s' % (archivedir,))

    _determine_os_name()
    _determine_os_version()
    _determine_download_platform()
    _determine_download_suffix()
    _determine_bindir()

    xpcshell = os.path.join(bindir, get_xpcshell_bin())
    logging.debug('sr xpcshell: %s' % (xpcshell,))

    xpcoutleaf = srxpcout
    logging.debug('sr xpcoutleaf: %s' % (xpcoutleaf,))
    try:
        xpctmp = _get_xpcshell_tmp()
        xpcoutdir = os.path.join(xpctmp, srxpcout)
        logging.debug('sr xpctmp: %s' % (xpctmp,))
        logging.debug('sr xpcoutdir: %s' % (xpcoutdir,))
    except OSError:
        # We only need this after the point where we can run xpcshell, so
        # don't worry if we can't get it earlier in the process
        logging.debug('xpcshell not available yet')
        pass

def run_process(*args, logger=logging):
    """Run a python process under the stoneridge environment
    """
    procname = args[0]
    command = [sys.executable] + args
    logger.debug('Running %s' % (procname,))
    logger.debug(' '.join(command))
    try:
        proc_stdout = subprocess.check_output(command,
                stderr=subprocess.STDOUT)
        logger.debug(proc_stdout)
        logger.debug('SUCCEEDED: %s' % (procname,))
    except subprocess.CalledProcessError, e:
        logger.error('FAILED: %s (%s)' % (procname, e.returncode))
        logger.error(e.output)
        raise # Do this in case caller has any special handling

_netconfig_ids = {
    'broadband':'0',
    'umts':'1',
    'gsm':'2',
}

_os_ids = {
    'windows':'w',
    'linux':'l',
    'mac':'m',
}

class ArgumentParser(argparse.ArgumentParser):
    """An argument parser for stone ridge programs that handles the arguments
    required by all of them
    """
    def __init__(self, **kwargs):
        argparse.ArgumentParser.__init__(self, **kwargs)

        self.add_argument('--config', dest='_sr_config_', required=True,
                help='Configuration file')
        self.add_argument('--netconfig', dest='_sr_netconfig_', required=True,
                help='Network Configuration in use', choices=netconfigs.keys())
        self.add_argument('--root', dest='_sr_root_', required=True,
                help='Root of Stone Ridge installation')
        self.add_argument('--workdir', dest='_sr_work_', required=True,
                help='Directory to do all the work in')
        self.add_argument('--xpcout', dest='_sr_xpcout_', default='stoneridge',
                help='Subdirectory of xpcshell temp to write output to')
        self.add_argument('--log', dest='_sr_log_', default=None, required=True,
                help='File to place log info in')

    def parse_args(self, **kwargs):
        global _conffile
        global current_netconfig
        global buildid_suffix

        args = argparse.ArgumentParser.parse_args(self, **kwargs)

        _conffile = args._sr_config_
        current_netconfig = args._sr_netconfig_
        logging.debug('sr _conffile: %s' % (_conffile,))
        logging.debug('sr current_netconfig: %s' % (current_netconfig,))

        setup_dirnames(args._sr_root_, args._sr_work_, args._sr_xpcout_)

        buildid_suffix = _os_ids[os_name] + _netconfig_ids[current_netconfig]
        logging.debug('sr buildid_suffix: %s' % (buildid_suffix,))

        return args

class QueueListener(object):
    def __init__(self, host, queue, **kwargs):
        self._host = host
        self._queue = queue
        self._params = pika.ConnectionParameters(host=host)
        self._args = kwargs
        self.setup(**kwargs)

    def setup(self):
        pass

    def handle(self, **kwargs):
        raise NotImplementedError

    def _handle(self, channel, method, properties, body):
        msg = json.loads(body)
        self.handle(**msg)
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def run(self):
        if self._queue is None:
            raise Exception('You must set queue for %s' % (type(self),))

        connection = pika.BlockingConnection(self._params)
        channel = connection.channel()

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(self._handle, queue=self._queue)

        channel.start_consuming()

class QueueWriter(object):
    def __init__(self, host, queue):
        self._host = host
        self._params = pika.ConnectionParameters(host=host)
        self._queue = queue

    def enqueue(self, **msg):
        connection = pika.BlockingConnection(self._params)
        channel = connection.channel()

        body = json.dumps(msg)
        channel.basic_publish(exchange='', routing_key=self._queue, body=body,
                properties=pika.BasicProperties(delivery_mode=2)) # Durable
        connection.close() # Ensures the message is sent

class RpcCaller(object):
    def __init__(self, host, outgoing_queue, incoming_queue):
        self._host = host
        self._outgoing_queue = outgoing_queue
        self._incoming_queue = incoming_queue

        params = pika.ConnectionParameters(host=host)
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel
        self._channel.basic_consume(self._on_rpc_done, no_ack=True,
                queue=self._incoming_queue)

    def _on_rpc_done(self, channel, method, properties, body):
        if self._srid == properties.correlation_id:
            self._response = body

    def __call__(self, **msg):
        if 'srid' not in msg:
            logging.error('Attempted to make an RPC call without an srid!')
            return None

        self._response = None
        self._srid = msg['srid']

        properties = pika.BasicProperties(reply_to=self._incoming_queue,
                correlation_id=self._srid)
        body = json.dumps(msg)
        self._channel.basic_publish(exchange='',
                routing_key=self._outgoing_queue, body=body,
                properties=properties)

        while self._response is None:
            self._connection.process_data_events()

        return json.loads(self._response)

class RpcHandler(QueueListener):
    def _handle(self, channel, method, properties, body):
        msg = json.loads(body)
        res = self.handle(**msg)

        body = json.dumps(res)
        res_properties = pika.BasicProperties(
                correlation_id=properties.correlation_id)
        channel.basic_publish(exchange='', routing_key=properties.reply_to,
                properties=res_properties, body=body)

        channel.basic_ack(delivery_tag=method.delivery_tag)
