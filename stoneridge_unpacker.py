import argparse
import glob
import os
import shutil
import subprocess

import stoneridge

class StoneRidgeUnpacker(object):
    def __new__(self, *args, **kwargs):
        sysname = stoneridge.system_name()
        if sysname == 'windows':
            return WindowsUnpacker()
        elif sysname == 'linux':
            return LinuxUnpacker()
        elif sysname == 'Mac':
            return MacUnpacker()

        raise ValueError, 'Invalid system type: %s' % (sysname,)

    def __init__(self, destdir, firefoxpkg, testzip):
        self.destdir = os.path.abspath(destdir)
        self.firefoxpkg = os.path.abspath(firefoxpkg)
        self.testzip = os.path.abspath(testzip)
        self.xpcshell = 'xpcshell'
        self.fxbindir = 'firefox'

    def run(self):
        # Make sure our destination directory exists and is empty
        if os.path.exists(self.destdir):
            shutil.rmtree(self.destdir)
        os.mkdir(self.destdir)

        # Get our firefox
        self.unpack_firefox()

        # Unzip the stuff we need from the tests zipfile
        unzipdir = os.path.join(self.destdir, 'unzip')
        os.mkdir(unzipdir)
        subprocess.call(['unzip', self.testzip, 'bin*'], cwd=unzipdir)

        # Put the xpcshell binary where it belongs
        xpcshell = os.path.join(unzipdir, 'bin', self.xpcshell)
        shutil.copy(xpcshell, self.fxbindir)

        # Put our components into place
        components = os.path.join(unzipdir, 'bin', 'components', '*')
        fxcomponents = os.path.join(self.fxbindir, 'components')
        subprocess.call(['bash', '-c',
            'cp -R "%s" "%s"' % (components, fxcomponents)])

        # Put the plugins in place, in case we need them
        fxplugins = os.path.join(self.fxbindir, 'plugins')
        if not os.path.exists(fxplugins):
            os.mkdir(fxplugins)
        plugins = os.path.join(unzipdir, 'bin', 'plugins', '*')
        subprocess.call(['bash', '-c',
            'cp -R "%s" "%s"' % (plugins, fxplugins)])

    def unpack_firefox(self):
        raise NotImplementedError

class WindowsUnpacker(StoneRidgeUnpacker):
    def __new__(*args, **kwargs):
        return object.__new__(WindowsUnpacker)

    def unpack_firefox(self):
        subprocess.call(['unzip', self.firefoxpkg], cwd=self.destdir)
        self.xpcshell = 'xpcshell.exe'

class LinuxUnpacker(StoneRidgeUnpacker):
    def __new__(*args, **kwargs):
        return object.__new__(LinuxUnpacker)

    def unpack_firefox(self):
        subprocess.call(['tar', 'xjvf', self.firefoxpkg], cwd=self.destdir)

class MacUnpacker(StoneRidgeUnpacker):
    def __new__(*args, **kwargs):
        return object.__new__(MacUnpacker)

    def unpack_firefox(self):
        mydir = os.path.split(__file__)[0]
        installdmg = os.path.join(mydir, 'installdmg.sh')
        subprocess.call(['/bin/bash', installdmg, self.firefoxpkg],
                cwd=self.destdir)

        pattern = os.path.join(self.destdir, '*.app')
        appdir = glob.glob(pattern)[0]
        appdir = os.path.basename(appdir)
        self.fxbindir = os.path.join(self.destdir, appdir, 'Contents', 'MacOS')

@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', dest='destdir', required=True,
            help='Directory to unpack to')
    parser.add_argument('-f', dest='firefoxpkg', required=True,
            help='Location of Firefox package')
    parser.add_argument('-t', dest='testzip', required=True,
            help='Location of test zipfile')

    args = parser.parse_args()

    unpacker = StoneRidgeUnpacker(args['destdir'], args['firefoxpkg'],
            args['testzip'])
    unpacker.run()
