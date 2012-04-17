import inspect
import platform
import sys
import traceback

_sys = None
_sys_ver = None
_dl_plat = None
_dl_suffix = None
_fx_bindir = None

def system_name():
    """Determine the os from platform.system
    """
    global _sys
    if _sys is None:
        _sys = platform.system().lower()
        if _sys == 'darwin':
            _sys = 'mac'
    return _sys

def system_version():
    """Determine the os version
    """
    global _sys_ver
    if _sys_ver is None:
        system = platform.system().lower()
        if system == 'linux':
            _sys_ver = ' '.join(platform.linux_distribution[0:2])
        elif system == 'darwin':
            _sys_ver = platform.mac_ver[0]
        elif system == 'windows':
            _sys_ver = platform.win32_ver()[1]
        else:
            _sys_ver = 'Unknown'
    return _sys_ver

def download_platform():
    """Determine which platform to download files for
    """
    global _dl_plat
    if _dl_plat is None:
        system = system_name()
        if system == 'linux':
            if platform.machine() == 'x86_64':
                _dl_plat = 'linux64'
            else:
                _dl_plat = 'linux32
        elif system == 'windows':
            if platform.machine() == 'x86_64':
                _dl_plat = 'win64'
            else:
                _dl_plat = 'win32'
        else:
            _dl_plat = system
    return _dl_plat

def download_suffix():
    """Determine the suffix of the firefox archive to download
    """
    global _dl_suffix
    if _dl_suffix is None:
        system = platform.system().lower()
        if system == 'linux':
            _dl_suffix = 'tar.bz2'
        elif system == 'darwin':
            _dl_suffix = 'dmg'
        else:
            _dl_suffix = 'zip'
    return _dl_suffix

def firefox_bindir():
    """Determine the location of the firefox binary based on platform
    """
    global _fx_bindir
    if _fx_bindir is None:
        system = platform.system().lower()
        if system == 'darwin':
            _fx_bindir = os.path.join('FirefoxNightly.app', 'Contents', 'MacOS')
        else:
            _fx_bindir = 'firefox'
    return _fx_bindir

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
