#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import logging
import os
import shutil
import subprocess
import zipfile

import stoneridge


class StoneRidgeUnpacker(object):
    """Unpacks the firefox archive and the tests zipfile and puts all the files
    in the right place. Most of this effort is common to all platforms, but
    some is platform-specific.
    """
    def __new__(self, *args, **kwargs):
        # The caller shouldn't care what platform its running on, so we
        # override __new__ to create the class that will unpack properly no
        # matter what
        os_name = stoneridge.get_config('machine', 'os')
        if os_name == 'windows':
            logging.debug('creating windows unpacker')
            return object.__new__(WindowsUnpacker)
        elif os_name == 'linux':
            logging.debug('creating linux unpacker')
            return object.__new__(LinuxUnpacker)
        elif os_name == 'mac':
            logging.debug('creating mac unpacker')
            return object.__new__(MacUnpacker)

        logging.critical('could not figure out what unpacker to create')
        raise ValueError('Invalid system type: %s' % (os_name,))

    def __init__(self):
        self.workdir = stoneridge.get_config('run', 'work')
        logging.debug('work directory: %s' % (self.workdir,))
        self.bindir = stoneridge.get_config('run', 'bin')
        logging.debug('bin directory: %s' % (self.bindir,))
        downloaddir = stoneridge.get_config('run', 'download')
        download_suffix = stoneridge.get_config('machine', 'download_suffix')
        self.firefoxpkg = os.path.join(downloaddir,
                                       'firefox.%s' % (download_suffix,))
        logging.debug('firefox package: %s' % (self.firefoxpkg,))
        self.testzip = os.path.join(downloaddir, 'tests.zip')
        logging.debug('test zip file: %s' % (self.testzip,))

    def _copy_tree(self, srcdir, name):
        logging.debug('_copy_tree(%s, %s)' % (srcdir, name))
        srcdir = os.path.join(srcdir, name)
        files = os.listdir(srcdir)
        dstdir = os.path.join(self.bindir, name)
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
        unzipdir = os.path.join(self.workdir, 'tests')
        logging.debug('creating unzip dir %s' % (unzipdir,))
        os.mkdir(unzipdir)
        z = zipfile.ZipFile(self.testzip, 'r')
        members = [f for f in z.namelist() if f.startswith('bin')]
        logging.debug('unzipping %s' % (str(members),))
        z.extractall(unzipdir, members)

        # Put the xpcshell binary where it belongs
        unzipbin = os.path.join(unzipdir, 'bin')
        xpcshell_bin = stoneridge.get_config('machine', 'xpcshell')
        xpcshell = os.path.join(unzipbin, xpcshell_bin)
        logging.debug('xpcshell: %s' % (xpcshell,))

        # Apparently xpcshell stopped being executable in the tests zip at some
        # point, so we need to fix that before copying
        logging.debug('setting permissions on xpcshell')
        os.chmod(xpcshell, 0755)

        logging.debug('copy xpcshell %s -> %s' % (xpcshell, self.bindir))
        shutil.copy(xpcshell, self.bindir)

        # Put our components into place
        logging.debug('copying components')
        self._copy_tree(unzipbin, 'components')

        # Put the plugins in place, in case we need them
        logging.debug('copying plugins')
        self._copy_tree(unzipbin, 'plugins')

        # Put the pageloader components into place
        srroot = stoneridge.get_config('stoneridge', 'root')
        pageloader = os.path.join(srroot, 'pageloader')
        self._copy_tree(pageloader, 'components')
        self._copy_tree(pageloader, 'chrome')

        # Now we need to put srdata.js into the appropriate place for it to be
        # picked up by the pageloader
        chrome = os.path.join(self.bindir, 'chrome')
        srdatasrc = os.path.join(srroot, 'srdata.js')
        srdatadst = os.path.join(chrome, 'srdata.js')
        if os.path.exists(srdatadst):
            os.unlink(srdatadst)
        logging.debug('copy srdata.js %s -> %s' % (srdatasrc, srdatadst))
        shutil.copyfile(srdatasrc, srdatadst)

        # Finally, we need to update chrome.manifest with the appropriate bits
        # from our local pageloader
        plmanifest = os.path.join(pageloader, 'chrome.manifest')
        fxmanifest = os.path.join(self.bindir, 'chrome.manifest')
        logging.debug('append %s to %s' % (plmanifest, fxmanifest))
        with file(fxmanifest, 'rb') as f:
            lines = f.readlines()
        with file(plmanifest, 'rb') as f:
            lines.extend(f.readlines())
        with file(fxmanifest, 'wb') as f:
            f.writelines(lines)

    def unpack_firefox(self):
        logging.critical('Base unpack_firefox called!')
        raise NotImplementedError('Use a subclass of StoneRidgeUnpacker')


class WindowsUnpacker(StoneRidgeUnpacker):
    def unpack_firefox(self):
        logging.debug('extracting windows firefox zip %s to %s' %
                      (self.firefoxpkg, self.workdir))
        z = zipfile.ZipFile(self.firefoxpkg, 'r')
        z.extractall(self.workdir)


class LinuxUnpacker(StoneRidgeUnpacker):
    def unpack_firefox(self):
        logging.debug('untarring linux package %s in %s' %
                      (self.firefoxpkg, self.workdir))
        subprocess.call(['tar', 'xjvf', self.firefoxpkg],
                        cwd=self.workdir)


class MacUnpacker(StoneRidgeUnpacker):
    def unpack_firefox(self):
        # MAC, Y U NO USE REGULAR ARCHIVE?!
        installroot = stoneridge.get_config('stoneridge', 'root')
        installdmg = os.path.join(installroot, 'installdmg.sh')
        logging.debug('mac using installdmg at %s' % (installdmg,))
        out = subprocess.check_output(['/bin/bash', installdmg,
                                       self.firefoxpkg],
                                      cwd=self.workdir,
                                      stderr=subprocess.STDOUT)
        logging.debug(out)


@stoneridge.main
def main():
    parser = stoneridge.TestRunArgumentParser()

    parser.parse_args()

    unpacker = StoneRidgeUnpacker()
    unpacker.run()
