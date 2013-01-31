# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import ConfigParser
import copy
import fcntl
import inspect
import json
import logging
import os
import platform
import resource
import signal
import subprocess
import sys
import traceback

import pika


# Names of netconfigs and operating systems
NETCONFIGS = ('broadband', 'umts', 'gsm')
OPERATING_SYSTEMS = ('linux', 'mac', 'windows')


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


_cp = None
_srconf = None
_runconf = None


def get_config_file():
    return _srconf


def get_config(section, option, default=None):
    """Read a config entry from the stoneridge ini files.
    """
    global _cp

    logging.debug('reading %s.%s (default %s)' %  (section, option, default))

    if _cp is None:
        _cp = ConfigParser.SafeConfigParser()

        if _srconf:
            logging.debug('loading stoneridge config file %s' % (_srconf,))
            _cp.read(_srconf)

        if _runconf:
            logging.debug('loading run config file %s' % (_runconf,))
            _cp.read(_runconf)

    try:
        val = _cp.get(section, option)
        logging.debug('found %s.%s, returning %s' % (section, option, val))
        return val
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError) as e:
        logging.debug('unable to find %s.%s, returning default %s' %
                (section, option, default))
        return default


def get_config_int(section, option, default=0):
    """Get an integer config variable from the stoneridge ini files
    """
    value = get_config(section, option, default=default)
    try:
        return int(value)
    except ValueError:
        logging.debug('invalid int value %s, returning default %s' %
                (value, default))
        return default


_xpcshell_environ = None


def run_xpcshell(args, stdout=subprocess.PIPE):
    """Run xpcshell with the appropriate args.
    """
    global _xpcshell_environ

    bindir = get_config('run', 'bin')
    if bindir is None:
        return (None, None)

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


_xpcoutdir = None


def get_xpcshell_output_directory():
    """Get the directory where xpcshell output will be placed.
    """
    global _xpcoutdir

    if _xpcoutdir is None:
        xpcoutleaf = get_config('run', 'xpcoutleaf')
        if xpcoutleaf is None:
            return None

        xpcshell_tmp_dir = None
        _, stdout = run_xpcshell(['-e',
            'dump("SR-TMP-DIR:" + '
            '     Components.classes["@mozilla.org/file/directory_service;1"]'
            '     .getService(Components.interfaces.nsIProperties)'
            '     .get("TmpD", Components.interfaces.nsILocalFile)'
            '     .path + "\\n");'
            'quit(0);'])

        for line in stdout:
            if line.startswith('SR-TMP-DIR:'):
                xpcshell_tmp_dir = line.strip().split(':', 1)[1]

        if xpcshell_tmp_dir is None:
            # TODO - maybe raise exception?
            return None

        _xpcoutdir = os.path.join(xpctmp, xpcoutleaf)

    return _xpcoutdir


_os_version = None


def get_os_version():
    """Return the OS version in use.
    """
    global _os_version

    if _os_version is None:
        os_name = get_config('machine', 'os')
        if os_name == 'linux':
            _os_version = ' '.join(platform.linux_distribution()[0:2])
        elif os_name == 'mac':
            _os_version = platform.mac_ver()[0]
        elif os_name == 'windows':
            _os_version = platform.win32_ver()[1]
        else:
            _os_version = 'Unknown'

    return _os_version


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


_buildid_suffix = None


def get_buildid_suffix():
    """Return the suffix to be used to uniquify the build id.
    """
    global _buildid_suffix

    if _buildid_suffix is None:
        os_name = get_config('machine', 'os')
        current_netconfig = get_config('run', 'netconfig')
        if os_name is None or current_netconfig is None:
            return ''

        _buildid_suffix = _os_ids[os_name] + _netconfig_ids[current_netconfig]

    return _buildid_suffix


_root = None


def run_process(procname, *args, **kwargs):
    """Run a python process under the stoneridge environment.
    """
    global _root

    if _root is None:
        _root = get_config('stoneridge', 'root')

    logger = kwargs.get('logger', logging)
    command = [sys.executable, os.path.join(_root, procname)] + map(str, args)
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


class ArgumentParser(argparse.ArgumentParser):
    """An argument parser for stone ridge programs that handles the arguments
    required by all of them.
    """
    def __init__(self, **kwargs):
        argparse.ArgumentParser.__init__(self, **kwargs)

        self.add_argument('--config', dest='_sr_config_', required=True,
                help='Configuration file')
        self.add_argument('--log', dest='_sr_log_', default=None, required=True,
                help='File to place log info in')

    def parse_args(self, **kwargs):
        global _srconf

        args = argparse.ArgumentParser.parse_args(self, **kwargs)

        _srconf = args._sr_config_
        logging.debug('_srconf: %s' % (_srconf,))
        logging.debug('_srlog: %s' % (args._sr_log_,))

        return args


def daemon_sig(pidfile):
    """Signal handler for daemons created with stoneridge.daemonize.
    """
    logging.debug('signal handler: unlinking pidfile')
    os.unlink(pidfile)
    logging.debug('signal handler: daemon exiting')
    sys.exit(0)


def daemonize(pidfile, function, **kwargs):
    """Run a function as a daemon.

    pidfile - Name of file to write PID to
    function - Function object to call as the daemon
    kwargs - Arguments to pass to <function>
    """
    logging.debug('forking for daemonization')
    pid = os.fork()

    if pid < 0:
        # Fork failure
        logging.error('fork failed (%s)' % (os.strerror(pid,)))
        sys.exit(1)

    if pid:
        # Parent
        sys.exit(0)

    sid = os.setsid()
    if sid == -1:
        # Error setting session ID
        logging.error('error setting sid')
        sys.exit(1)

    devnull = getattr(os, 'devnull', '/dev/null')
    logging.debug('devnull = %s' % (devnull,))

    log_fds = set()
    logger = logging.getLogger()
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            log_fds.add(handler.stream.fileno())
    logging.debug('log fds = %s' % (log_fds,))

    for fd in range(resource.getrlimit(resource.RLIMIT_NOFILE)[0]):
        if fd in log_fds:
            logging.debug('not closing fd %s (log)' % (fd,))
        else:
            try:
                os.close(fd)
                logging.debug('closed fd %s' % (fd,))
            except OSError:
                # Didn't have it open, don't care
                pass

    # Make stdin, stdout & stderr point to /dev/null
    logging.debug('pointing std{in,out,err} -> devnull')
    os.open(devnull, os.O_RDWR)
    os.dup(0)
    os.dup(0)

    # Set a sane umask
    logging.debug('setting umask 027')
    os.umask(027)

    # Change to the usual daemon directory
    logging.debug('chdir -> /')
    os.chdir('/')

    with file(pidfile, 'w') as f:
        logging.debug('locking %s' % (pidfile,))
        fcntl.lockf(f, fcntl.LOCK_EX|fcntl.LOCK_NB)

        logging.debug('writing pid')
        f.write('%s' % (os.getpid(),))
        f.flush()

        logging.debug('setting up sigterm handler')
        signal.signal(signal.SIGTERM, lambda sig, frame: daemon_sig(pidfile))

        logging.debug('calling daemon function')
        function(**kwargs)

        # If we get here, we assume the program is exiting cleanly
        logging.debug('unlinking pidfile')
        os.unlink(pidfile)
        logging.debug('daemon exiting')
        sys.exit(0)


class DaemonArgumentParser(ArgumentParser):
    """An argument parser for stone ridge programs that run as daemons.
    """
    def __init__(self, **kwargs):
        ArgumentParser.__init__(self, **kwargs)

        self.add_argument('--nodaemon', dest='nodaemon', action='store_true')
        self.add_argument('--pidfile', dest='pidfile')

    def do_exit(self, msg):
        self.print_usage()
        self.exit(2, msg % (self.prog,))

    def do_mutex_exit(self, arg):
        msg = '%%s: error: argument %s: not allowed with argument --nodaemon\n'
        self.do_exit(msg % (arg,))

    def do_missing_exit(self, arg):
        msg = '%%s: error: argument %s is required\n'
        self.do_exit(msg % (arg,))

    def parse_args(self, **kwargs):
        self.args = ArgumentParser.parse_args(self, **kwargs)

        if self.args.nodaemon:
            if self.args.pidfile:
                self.do_mutex_exit('--pidfile')
        elif not self.args.pidfile:
            self.do_missing_exit('--pidfile')

        return self.args

    def start_daemon(self, daemon_func, **kwargs):
        if self.args.nodaemon:
            logging.debug('not running daemonized')
            daemon_func(**kwargs)
            sys.exit(0)

        logging.debug('starting daemon')
        daemonize(self.args.pidfile, daemon_func, **kwargs)


class TestRunArgumentParser(ArgumentParser):
    """Like stoneridge.ArgumentParser, but adds arguments specific for programs
    that are run as part of a test run.
    """
    def __init__(self, **kwargs):
        ArgumentParser.__init__(self, **kwargs)

        self.add_argument('--runconfig', dest='_sr_runconfig_', required=True,
                help='Run-specific configuration file')

    def parse_args(self, **kwargs):
        global _runconf

        args = ArgumentParser.parse_args(self, **kwargs)

        _runconf = args._sr_runconfig_
        logging.debug('_runconf: %s' % (_runconf,))

        return args


class QueueListener(object):
    """A class to be used as the base for stone ridge daemons that need to
    respond to entries on a queue.
    """
    def __init__(self, queue, **kwargs):
        self._host = get_config('stoneridge', 'mqhost')
        self._queue = queue
        self._params = pika.ConnectionParameters(host=self._host)
        self._args = kwargs
        self.setup(**kwargs)

    def setup(self, **kwargs):
        """Used for class-specific things that would normally go in __init__.
        """
        pass

    def handle(self, **kwargs):
        """The callback that is called when a message is received on the queue.
        All subclasses must override this. Nothing is done with the returned
        value.
        """
        raise NotImplementedError

    def _handle(self, channel, method, properties, body):
        """Internal callback for when a message is received. Deserializes the
        message and calls handle. Once handle succeeds, the message is
        acknowledged.
        """
        msg = json.loads(body)
        self.handle(**msg)
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def run(self):
        """Main event loop for a queue listener.
        """
        logging.debug('Running queue listener for %s' % (self._queue,))
        if self._queue is None:
            raise Exception('You must set queue for %s' % (type(self),))

        connection = pika.BlockingConnection(self._params)
        channel = connection.channel()

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(self._handle, queue=self._queue)

        channel.start_consuming()


class QueueWriter(object):
    """Used when someone needs to write to a stone ridge queue.
    """
    def __init__(self, queue):
        self._host = get_config('stoneridge', 'mqhost')
        self._params = pika.ConnectionParameters(host=self._host)
        self._queue = queue

    def enqueue(self, **msg):
        """Place a message on the queue. The message is serialized as a JSON
        string before being placed on the queue.
        """
        connection = pika.BlockingConnection(self._params)
        channel = connection.channel()

        body = json.dumps(msg)
        channel.basic_publish(exchange='', routing_key=self._queue, body=body,
                properties=pika.BasicProperties(delivery_mode=2)) # Durable
        connection.close() # Ensures the message is sent


def enqueue(nightly=True, ldap='', sha='', netconfigs=None,
        operating_systems=None):
    """Convenience function to kick off a test run. If called with no arguments,
    this will kick off a run for all operating systems with all netconfigs
    against the latest nightly build.
    """
    if netconfigs is None:
        netconfigs = _netconfig_ids.keys()
    else:
        for nc in netconfigs:
            if nc not in _netconfig_ids:
                raise ValueError('Invalid net config %s' % (nc,))

    if operating_systems is None:
        operating_systems = _os_ids.keys()
    else:
        for ops in operating_systems:
            if ops not in _os_ids:
                raise ValueError('Invalid operating system %s' % (nc,))

    if nightly:
        if ldap or sha:
            raise ValueError('ldap and sha are not compatible with nightly')
    else:
        if not ldap or not sha:
            raise ValueError('both ldap and sha must be set')

    writer = QueueWriter(INCOMING_QUEUE)
    writer.enqueue(nightly=nightly, ldap=ldap, sha=sha, netconfigs=netconfigs,
            operating_systems=operating_systems)


class RpcCaller(object):
    """Used to call remote functions via the stone ridge mq of choice.
    """
    def __init__(self, outgoing_queue, incoming_queue):
        self._host = get_config('stoneridge', 'mqhost')
        self._outgoing_queue = outgoing_queue
        self._incoming_queue = incoming_queue

        params = pika.ConnectionParameters(host=self._host)
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel
        self._channel.basic_consume(self._on_rpc_done, no_ack=True,
                queue=self._incoming_queue)

    def _on_rpc_done(self, channel, method, properties, body):
        """The callback that is called when the remote function call
        is complete.
        """
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
    """Like stoneridge.QueueListener, but for programs that service RPC instead
    of asynchronous queue events.
    """
    def handle(self, **kwargs):
        """Just like stoneridge.QueueListener.handle, except the return value
        from this must be serializable as a JSON string.
        """
        raise NotImplementedError

    def _handle(self, channel, method, properties, body):
        """Internal message callback to perform the RPC and return the result
        to the caller.
        """
        msg = json.loads(body)
        res = self.handle(**msg)

        body = json.dumps(res)
        res_properties = pika.BasicProperties(
                correlation_id=properties.correlation_id)
        channel.basic_publish(exchange='', routing_key=properties.reply_to,
                properties=res_properties, body=body)

        channel.basic_ack(delivery_tag=method.delivery_tag)
