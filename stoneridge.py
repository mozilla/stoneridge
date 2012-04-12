import inspect
import platform
import sys
import traceback

def system_name():
    """Determine the os from platform.system
    """
    system = platform.system().lower()
    if system == 'darwin':
        system = 'mac'
    return system

def system_version():
    """Determine the os version
    """
    system = platform.system().lower()
    if system == 'linux':
        return ' '.join(platform.linux_distribution[0:2])
    if system == 'darwin':
        return platform.mac_ver[0]
    if system == 'windows':
        return platform.win32_ver()[1]
    return 'Unknown'

def download_platform():
    system = system_name()
    if system == 'linux':
        if platform.machine() == 'x86_64':
            return 'linux64'
        return 'linux32
    if system == 'windows':
        if platform.machine() == 'x86_64':
            return 'win64'
        return 'win32'
    return system

def download_suffix():
    system = platform.system().lower()
    if system == 'linux':
        return 'tar.gz'
    if system == 'darwin':
        return 'dmg'
    return 'zip'

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
