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

import logging

class StoneRidgeUnpacker(object):
    """Unpacks the firefox archive and the tests zipfile and puts all the files
    in the right place. Most of this effort is common to all platforms, but some
    is platform-specific.
    """
    def __new__(self, *args, **kwargs):
        # The caller shouldn't care what platform its running on, so we override
        # __new__ to create the class that will unpack properly no matter what
        if stoneridge.os_name == 'windows':
            logging.debug('creating windows unpacker')
            return object.__new__(WindowsUnpacker)
        elif stoneridge.os_name == 'linux':
            logging.debug('creating linux unpacker')
            return object.__new__(LinuxUnpacker)
        elif stoneridge.os_name == 'mac':
            logging.debug('creating mac unpacker')
            return object.__new__(MacUnpacker)

        logging.critical('could not figure out what unpacker to create')
        raise ValueError, 'Invalid system type: %s' % (sysname,)

    def __init__(self):
        self.firefoxpkg = os.path.join(stoneridge.downloaddir,
                'firefox.%s' % (stoneridge.download_suffix,))
        logging.debug('firefox package: %s' % (self.firefoxpkg,))
        self.testzip = os.path.join(stoneridge.downloaddir, 'tests.zip')
        logging.debug('test zip file: %s' % (self.testzip,))

    def _copy_tree(self, unzipdir, name):
        logging.debug('_copy_tree(%s, %s)' % (unzipdir, name))
        srcdir = os.path.join(unzipdir, 'bin', name)
        files = os.listdir(srcdir)
        dstdir = os.path.join(stoneridge.bindir, name)
        logging.debug('srcdir: %s' % (srcdir,))
        logging.debug('files: %s' % (files,))
        logging.debug('dstdir: %s' % (dstdir,))
        if not os.path.exists(dstdir):
            logging.debug('creating %s' % (dstdir,))
            os.mkdir(dstdir)
        for f in files:
            src = os.path.join(srcdir, f)
            dst = os.path.join(dstdir, f)
            if os.path.isdir(src):
                logging.debug('recursive copy %s -> %s' % (src, dst))
                shutil.copytree(src, dst)
            else:
                logging.debug('copy %s -> %s' % (src, dst))
                shutil.copyfile(src, dst)

    def run(self):
        logging.debug('unpacker running')
        # Get our firefox
        logging.debug('unpacking firefox')
        self.unpack_firefox()

        # Unzip the stuff we need from the tests zipfile
        unzipdir = os.path.join(stoneridge.workdir, 'tests')
        logging.debug('creating unzip dir %s' % (unzipdir,))
        os.mkdir(unzipdir)
        z = zipfile.ZipFile(self.testzip, 'r')
        members = [f for f in z.namelist() if f.startswith('bin')]
        logging.debug('unzipping %s' % (str(members),))
        z.extractall(unzipdir, members)

        # Put the xpcshell binary where it belongs
        xpcshell = os.path.join(unzipdir, 'bin', stoneridge.get_xpcshell_bin())
        logging.debug('xpcshell: %s' % (xpcshell,))

        # Apparently xpcshell stopped being executable in the tests zip at some
        # point, so we need to fix that before copying
        logging.debug('setting permissions on xpcshell')
        os.chmod(xpcshell, 0755)

        logging.debug('copy xpcshell %s -> %s' % (xpcshell, stoneridge.bindir))
        shutil.copy(xpcshell, stoneridge.bindir)

        # Put our components into place
        logging.debug('copying components')
        self._copy_tree(unzipdir, 'components')

        # Put the plugins in place, in case we need them
        logging.debug('copying plugins')
        self._copy_tree(unzipdir, 'plugins')

    def unpack_firefox(self):
        logging.critical('Base unpack_firefox called!')
        raise NotImplementedError, 'Use a subclass of StoneRidgeUnpacker'

class WindowsUnpacker(StoneRidgeUnpacker):
    def unpack_firefox(self):
        logging.debug('extracting windows firefox zip %s to %s' %
                (self.firefoxpkg, stoneridge.workdir))
        z = zipfile.ZipFile(self.firefoxpkg, 'r')
        z.extractall(stoneridge.workdir)

class LinuxUnpacker(StoneRidgeUnpacker):
    def unpack_firefox(self):
        logging.debug('untarring linux package %s in %s' %
                (self.firefoxpkg, stoneridge.workdir))
        subprocess.call(['tar', 'xjvf', self.firefoxpkg],
                cwd=stoneridge.workdir)

class MacUnpacker(StoneRidgeUnpacker):
    def unpack_firefox(self):
        # MAC, Y U NO USE REGULAR ARCHIVE?!
        installdmg = os.path.join(stoneridge.installroot, 'installdmg.sh')
        logging.debug('mac using installdmg at %s' % (installdmg,))
        out = subprocess.check_output(['/bin/bash', installdmg, self.firefoxpkg],
                cwd=stoneridge.workdir, stderr=subprocess.STDOUT)
        logging.debug(out)

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()

    args = parser.parse_args()

    unpacker = StoneRidgeUnpacker()
    unpacker.run()
