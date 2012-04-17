# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import inspect
import platform
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

def main(_main):
    """Mark a function as the main function to run when run as a script.
    If that function throws an exception, we'll print the traceback to
    stderr and exit.
    """
    parent = inspect.stack()[1][0]
    name = parent.f_locals.get('__name__', None)
    if name == '__main__':
        try:
            _main()
        except Exception, e:
            traceback.print_tb(sys.exc_info()[2], None, sys.stderr)
            sys.exit(1)
        sys.exit(0)
    return _main

def update(conffile):
    """Update the stone ridge installation from the latest source
    """
    # TODO
    pass

class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, **kwargs):
        argparse.ArgumentParser.__init__(self, **kwargs)

        self.add_argument('--root', dest='_sr_root_', required=True,
                help='Root of Stone Ridge installation')
        self.add_argument('--workdir', dest='_sr_work_', required=True,
                help='Directory to do all the work in')

    @staticmethod
    def _determine_os_name(self):
        """Determine the os from platform.system
        """
        global os_name
        os_name = platform.system().lower()
        if os_name == 'darwin':
            os_name = 'mac'

    @staticmethod
    def _determine_os_version():
        """Determine the os version
        """
        global os_version
        if os_name == 'linux':
            os_version = ' '.join(platform.linux_distribution[0:2])
        elif os_name == 'mac':
            os_version = platform.mac_ver[0]
        elif system == 'windows':
            os_version = platform.win32_ver()[1]
        else:
            os_version = 'Unknown'

    @staticmethod
    def _determine_download_platform():
        """Determine which platform to download files for
        """
        global download_platform
        if os_name == 'linux':
            if platform.machine() == 'x86_64':
                download_platform = 'linux64'
            else:
                download_platform = 'linux32
        elif os_name == 'windows':
            if platform.machine() == 'x86_64':
                download_platform = 'win64'
            else:
                download_platform = 'win32'
        else:
            download_platform = os_name

    @staticmethod
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

    @staticmethod
    def _determine_bindir():
        """Determine the location of the firefox binary based on platform
        """
        global bindir
        if os_name == 'mac':
            bindir = os.path.join(workdir, 'FirefoxNightly.app', 'Contents',
                    'MacOS')
        else:
            bindir = os.path.join(workdir, 'firefox')

    @staticmethod
    def setup_dirnames(srroot, srwork):
        global installroot
        global workdir
        global downloaddir
        global testroot
        global outdir
        global archivedir
        global logdir

        installroot = os.path.abspath(srroot)
        workdir = os.path.abspath(srwork)
        downloaddir = os.path.join(workdir, 'dl')
        testroot = os.path.join(installroot, 'tests')
        outdir = os.path.join(workdir, 'out')
        archivedir = os.path.join(installroot, 'archives')
        logdir = os.path.join(installroot, 'logs')

        ArgumentParser._determine_os_name()
        ArgumentParser._determine_os_version()
        ArgumentParser._determine_download_platform()
        ArgumentParser._determine_download_suffix()
        ArgumentParser._determine_bindir()

    def parse_args(self, **kwargss):
        args = argparse.ArgumentParser.parse_args(self, **kwargs)

        self.setup_dirnames(args['_sr_root_'], args['_sr_work_'])

        return args
