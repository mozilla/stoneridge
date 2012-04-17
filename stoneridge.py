import inspect
import platform
import sys
import traceback

# General information common to all stoneridge programs
system_name = None
system_version = None
download_platform = None
download_suffix = None

# Paths that multiple programs need to know about
installroot = None
workdir = None
dldir = None
bindir = None
testroot = None
outdir = None

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

class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, **kwargs):
        ArgumentParser.__init__(self, **kwargs)

        self.add_argument('--root', dest='_sr_root_', required=True,
                help='Root of Stone Ridge installation')
        self.add_argument('--workdir', dest='_sr_work_', required=True,
                help='Directory to do all the work in')

    def _determine_system_name(self):
        """Determine the os from platform.system
        """
        global system_name
        system_name = platform.system().lower()
        if system_name == 'darwin':
            system_name = 'mac'

    def _determine_system_version():
        """Determine the os version
        """
        global system_version
        if system_name == 'linux':
            system_version = ' '.join(platform.linux_distribution[0:2])
        elif system_name == 'mac':
            system_version = platform.mac_ver[0]
        elif system == 'windows':
            system_version = platform.win32_ver()[1]
        else:
            system_version = 'Unknown'

    def _determine_download_platform():
        """Determine which platform to download files for
        """
        global download_platform
        if system_name == 'linux':
            if platform.machine() == 'x86_64':
                download_platform = 'linux64'
            else:
                download_platform = 'linux32
        elif system_name == 'windows':
            if platform.machine() == 'x86_64':
                download_platform = 'win64'
            else:
                download_platform = 'win32'
        else:
            download_platform = system_name

    def _determine_download_suffix():
        """Determine the suffix of the firefox archive to download
        """
        global download_suffix
        if system_name == 'linux':
            download_suffix = 'tar.bz2'
        elif system_name == 'mac':
            download_suffix = 'dmg'
        else:
            download_suffix = 'zip'

    def _determine_firefox_bindir():
        """Determine the location of the firefox binary based on platform
        """
        global bindir
        if system_name == 'mac':
            bindir = os.path.join(workdir, 'FirefoxNightly.app', 'Contents',
                    'MacOS')
        else:
            bindir = os.path.join(workdir, 'firefox')

    def parse_args(self, **kwargss):
        global installroot
        global workdir
        global dldir
        global testroot
        global outdir

        args = ArgumentParser.parse_args(self, **kwargs)

        installroot = os.path.abspath(args['_sr_root_'])
        workdir = os.path.abspath(args['_sr_work_'])
        dldir = os.path.join(workdir, 'dl')
        testroot = os.path.join(installroot, 'tests')
        outdir = os.path.join(workdir, 'out')

        self._determine_system_name()
        self._determine_system_version()
        self._determine_download_platform()
        self._determine_download_suffix()
        self._determine_firefox_bindir()

        return args
