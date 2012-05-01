# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import ConfigParser
import inspect
import platform
import StringIO
import subprocess
import sys
import traceback

# General information common to all stoneridge programs
os_name = None
os_version = None
download_platform = None
download_suffix = None

# Paths that multiple programs need to know about
installroot = None
workdir = None
downloaddir = None
bindir = None
testroot = None
outdir = None
archivedir = None
logdir = None

# Misc configuration
_debug_enabled = True # Use False for production

def main(_main):
    """Mark a function as the main function to run when run as a script.
    If that function throws an exception, we'll print the traceback to
    stderr and exit.
    """
    parent = inspect.stack()[1][0]
    name = parent.f_locals.get('__name__', None)
    if name == '__main__':
        rval = 0
        try:
            _main()
        except Exception, e:
            traceback.print_exception(type(e), e, sys.exc_info()[2], None,
                    sys.stderr)
            sys.exit(1)
        sys.exit(rval)
    return _main

def debug(msg):
    if _debug_enabled:
        sys.stderr.write(msg)

def update(conffile):
    """Update the stone ridge installation from the latest source
    """
    cp = ConfigParser.SafeConfigParser()
    cp.load([conffile])

    try:
        scheme = cp.get('update', 'scheme')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), e:
        return

    try:
        url = cp.get('update', 'url')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), e:
        url = None

    if scheme == 'hg':
        args = ['hg', 'pull', '-u']
    elif scheme == 'git':
        args = ['git', 'pull']
    else:
        return

    if url:
        args.append(url)

    outbuf = StringIO.StringIO()
    if subprocess.call(args, stdout=outbuf, stderr=subprocess.STDOUT):
        sys.stderr.write('Error updating Stone Ridge\n')
        sys.stderr.write(outbuf.getvalue())
    outbuf.close()

def run_xpcshell(args, stdout=subprocess.PIPE):
    """Run xpcshell with the appropriate args
    """
    xpcargs = [xpcshell] + args
    proc = subprocess.Popen(xpcargs, stdout=stdout,
            stderr=subprocess.STDOUT, cwd=bindir)
    res = proc.wait()
    return (res, proc.stdout)

def get_xpcshell_tmp():
    """Determine the temporary directory as xpcshell thinks of it
    """
    # TODO - make sure this works on windows to create a file in python
    _, stdout = run_xpcshell(['-e',
        'dump("SR-TMP-DIR:" + '
        '     Components.classes["@mozilla.org/file/directory_service;1"]'
        '     .getService(Components.interfaces.nsIProperties)'
        '     .get("TmpD", Components.interfaces.nsILocalFile)'
        '     .path + "\n");'
        'quit(0);'])
    for line in stdout:
        if line.startswith('SR-TMP-DIR:'):
            return line.strip().split(':', 1)[1]

def get_xpcshell_bin():
    """Return the name of the xpcshell binary
    """
    if os_name == 'windows':
        return 'xpcshell.exe'
    return 'xpcshell'

def _determine_os_name(self):
    """Determine the os from platform.system
    """
    global os_name
    os_name = platform.system().lower()
    if os_name == 'darwin':
        os_name = 'mac'

def _determine_os_version():
    """Determine the os version
    """
    global os_version
    if os_name == 'linux':
        os_version = ' '.join(platform.linux_distribution[0:2])
    elif os_name == 'mac':
        os_version = platform.mac_ver[0]
    elif os_name == 'windows':
        os_version = platform.win32_ver()[1]
    else:
        os_version = 'Unknown'

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

def _determine_bindir():
    """Determine the location of the firefox binary based on platform
    """
    global bindir
    if os_name == 'mac':
        bindir = os.path.join(workdir, 'FirefoxNightly.app', 'Contents',
                'MacOS')
    else:
        bindir = os.path.join(workdir, 'firefox')

def setup_dirnames(srroot, srwork):
    """Determine the directory names and platform information to be used
    by this run of stone ridge
    """
    global installroot
    global workdir
    global downloaddir
    global testroot
    global outdir
    global archivedir
    global logdir
    global xpcshell

    installroot = os.path.abspath(srroot)
    workdir = os.path.abspath(srwork)
    downloaddir = os.path.join(workdir, 'dl')
    testroot = os.path.join(installroot, 'tests')
    outdir = os.path.join(workdir, 'out')
    archivedir = os.path.join(installroot, 'archives')
    logdir = os.path.join(installroot, 'logs')

    _determine_os_name()
    _determine_os_version()
    _determine_download_platform()
    _determine_download_suffix()
    _determine_bindir()

    xpcshell = os.path.join(bindir, get_xpcshell_bin())

class ArgumentParser(argparse.ArgumentParser):
    """An argument parser for stone ridge programs that handles the arguments
    required by all of them
    """
    def __init__(self, **kwargs):
        argparse.ArgumentParser.__init__(self, **kwargs)

        self.add_argument('--root', dest='_sr_root_', required=True,
                help='Root of Stone Ridge installation')
        self.add_argument('--workdir', dest='_sr_work_', required=True,
                help='Directory to do all the work in')

    def parse_args(self, **kwargss):
        args = argparse.ArgumentParser.parse_args(self, **kwargs)

        setup_dirnames(args['_sr_root_'], args['_sr_work_'])

        return args
