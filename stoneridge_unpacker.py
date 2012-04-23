#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import os
import shutil
import subprocess

import stoneridge

class StoneRidgeUnpacker(object):
    """Unpacks the firefox archive and the tests zipfile and puts all the files
    in the right place. Most of this effort is common to all platforms, but some
    is platform-specific.
    """
    def __new__(self, *args, **kwargs):
        # The caller shouldn't care what platform its running on, so we override
        # __new__ to create the class that will unpack properly no matter what
        if stoneridge.os_name == 'windows':
            return WindowsUnpacker()
        elif stoneridge.os_name == 'linux':
            return LinuxUnpacker()
        elif stoneridge.os_name == 'mac':
            return MacUnpacker()

        raise ValueError, 'Invalid system type: %s' % (sysname,)

    def __init__(self):
        self.firefoxpkg = os.path.join(stoneridge.downloaddir,
                'firefox.%s' % (stoneridge.download_suffix,))
        self.testzip = os.path.join(stoneridge.downloaddir, 'tests.zip')

    def run(self):
        # Get our firefox
        self.unpack_firefox()

        # Unzip the stuff we need from the tests zipfile
        unzipdir = os.path.join(stoneridge.workdir, 'unzip')
        os.mkdir(unzipdir)
        subprocess.call(['unzip', self.testzip, 'bin*'], cwd=unzipdir)

        # Put the xpcshell binary where it belongs
        xpcshell = os.path.join(unzipdir, 'bin', stoneridge.get_xpcshell_bin())
        shutil.copy(xpcshell, stoneridge.bindir)

        # Put our components into place
        components = os.path.join(unzipdir, 'bin', 'components', '*')
        fxcomponents = os.path.join(stoneridge.bindir, 'components')
        subprocess.call(['bash', '-c',
            'cp -R "%s" "%s"' % (components, fxcomponents)])

        # Put the plugins in place, in case we need them
        fxplugins = os.path.join(stoneridge.bindir, 'plugins')
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
        subprocess.call(['unzip', self.firefoxpkg], cwd=stoneridge.workdir)

class LinuxUnpacker(StoneRidgeUnpacker):
    def __new__(*args, **kwargs):
        return object.__new__(LinuxUnpacker)

    def unpack_firefox(self):
        subprocess.call(['tar', 'xjvf', self.firefoxpkg],
                cwd=stoneridge.workdir)

class MacUnpacker(StoneRidgeUnpacker):
    def __new__(*args, **kwargs):
        return object.__new__(MacUnpacker)

    def unpack_firefox(self):
        # MAC, Y U NO USE REGULAR ARCHIVE?!
        installdmg = os.path.join(stoneridge.installroot, 'installdmg.sh')
        subprocess.call(['/bin/bash', installdmg, self.firefoxpkg],
                cwd=stoneridge.workdir)

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()

    args = parser.parse_args()

    unpacker = StoneRidgeUnpacker()
    unpacker.run()
