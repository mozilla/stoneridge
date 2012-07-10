#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import glob
import os
import shutil
import subprocess
import zipfile

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
            return object.__new__(WindowsUnpacker)
        elif stoneridge.os_name == 'linux':
            return object.__new__(LinuxUnpacker)
        elif stoneridge.os_name == 'mac':
            return object.__new__(MacUnpacker)

        raise ValueError, 'Invalid system type: %s' % (sysname,)

    def __init__(self):
        self.firefoxpkg = os.path.join(stoneridge.downloaddir,
                'firefox.%s' % (stoneridge.download_suffix,))
        self.testzip = os.path.join(stoneridge.downloaddir, 'tests.zip')

    def _copy_tree(self, unzipdir, name):
        srcdir = os.path.join(unzipdir, 'bin', name)
        files = os.listdir(srcdir)
        dstdir = os.path.join(stoneridge.bindir, name)
        if not os.path.exists(dstdir):
            os.mkdir(dstdir)
        for f in files:
            src = os.path.join(srcdir, f)
            dst = os.path.join(dstdir, f)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copyfile(src, dst)

    def run(self):
        # Get our firefox
        self.unpack_firefox()

        # Unzip the stuff we need from the tests zipfile
        unzipdir = os.path.join(stoneridge.workdir, 'tests')
        os.mkdir(unzipdir)
        z = zipfile.ZipFile(self.testzip, 'r')
        members = [f for f in z.namelist() if f.startswith('bin')]
        z.extractall(unzipdir, members)

        # Put the xpcshell binary where it belongs
        xpcshell = os.path.join(unzipdir, 'bin', stoneridge.get_xpcshell_bin())
        shutil.copy(xpcshell, stoneridge.bindir)

        # Put our components into place
        self._copy_tree(unzipdir, 'components')

        # Put the plugins in place, in case we need them
        self._copy_tree(unzipdir, 'plugins')

    def unpack_firefox(self):
        raise NotImplementedError

class WindowsUnpacker(StoneRidgeUnpacker):
    def unpack_firefox(self):
        z = zipfile.ZipFile(self.firefoxpkg, 'r')
        z.extractall(stoneridge.workdir)

class LinuxUnpacker(StoneRidgeUnpacker):
    def unpack_firefox(self):
        subprocess.call(['tar', 'xjvf', self.firefoxpkg],
                cwd=stoneridge.workdir)

class MacUnpacker(StoneRidgeUnpacker):
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
