#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import ftplib
import logging
import os
import requests
import shutil
import time

import stoneridge

class cwd(object):
    """A context manager to change our working directory when we enter the
    context, and then change back to the original working directory when we
    exit the context
    """
    def __init__(self, dirname):
        self.newcwd = dirname
        self.oldcwd = os.getcwd()
        logging.debug('creating cwd object with newcwd %s and oldcwd %s' %
                (self.newcwd, self.oldcwd))

    def __enter__(self):
        logging.debug('changing cwd to %s' % (self.newcwd,))
        os.chdir(self.newcwd)

    def __exit__(self, *args):
        logging.debug('returning cwd to %s' % (self.oldcwd,))
        os.chdir(self.oldcwd)

class StoneRidgeCloner(object):
    """This runs on the central stone ridge server, and downloads releases from
    ftp.m.o to a local directory that is served up to the clients by a plain ol'
    web server. Those clients use stoneridge_downloader.py to get the files they
    need from the central server.
    """
    def __init__(self, path, nightly, srid, linux, mac, windows):
        self.host = stoneridge.get_config('cloner', 'host')
        root = stoneridge.get_config('cloner', 'root')
        self.path = '/'.join(root, path)
        self.nightly = nightly
        self.outroot = stoneridge.get_config('server', 'downloads')
        self.tstamp = time.strftime('%Y%m%d%H%M%S', time.gmtime())
        self.outdir = os.path.join(self.outroot, srid)
        self.keep = stoneridge.get_config('server', 'keep', default=50)
        self.linux = linux
        self.mac = mac
        self.windows = windows

        if not os.path.exists(self.outroot):
            os.mkdir(self.outroot)

        logfile = os.path.join(self.outroot, 'cloner_%s.log' % (self.tstamp,))
        logging.basicConfig(filename=logfile, level=logging.DEBUG,
                format=stoneridge.log_fmt)
        logging.debug('host: %s' % (self.host,))
        logging.debug('path: %s' % (self.path,))
        logging.debug('nightly: %s' % (self.nightly,))
        logging.debug('output root: %s' % (self.outroot,))
        logging.debug('timestamp: %s' % (self.tstamp,))
        logging.debug('output directory: %s' % (self.outdir,))
        logging.debug('keep history: %s' % (self.keep,))
        logging.debug('linux: %s' % (self.linux,))
        logging.debug('mac: %s' % (self.mac,))
        logging.debug('windows: %s' % (self.windows,))

        self.prefix = ''

    def _gather_filelist(self):
        """Get the list of files available on our FTP server

        Returns: list of filenames relative to the path on the server
        """
        logging.debug('gathering files from ftp server')
        ftp = ftplib.FTP(self.host)
        ftp.login()
        ftp.cwd(self.path)
        files = ftp.nlst()
        ftp.quit()
        logging.debug('files on server: %s' % (files,))
        return files

    def _build_dl_url(self, fname):
        """Create a download (https) URL for a particular file

        Returns: a URL string
        """
        logging.debug('creating download url for %s' % (fname,))
        remotefile = os.path.join(self.path, fname)
        logging.debug('remote filename: %s' % (remotefile,))
        url = 'https://%s%s' % (self.host, remotefile)
        logging.debug('url: %s' % (url,))
        return url

    def _get_prefix(self, files):
        """Get the filename prefix that is common to all the files we'll need to
        download

        Returns: <prefix (string)>
        """
        logging.debug('getting filename prefix')
        prefixfile = [f for f in files if f.endswith('.mac.checksums.asc')][-1]
        prefix = prefixfile.replace('.mac.checksums.asc', '')
        logging.debug('filename prefix: %s' % (prefix,))
        return prefix

    def _ensure_outdir(self, platform):
        """Ensure the output directory for a platform exists
        """
        logging.debug('ensuring output directory for %s exists' % (platform,))
        if not os.path.exists(self.outdir):
            logging.debug('creating outdir %s' % (self.outdir,))
            os.mkdir(self.outdir)
        platdir = os.path.join(self.outdir, platform)
        logging.debug('platform directory: %s' % (platdir,))
        if not os.path.exists(platdir):
            logging.debug('creating platform directory %s' % (platdir,))
            os.mkdir(platdir)

    def _dl_to_file(self, url, outfile):
        """Download the file at <url> and save it to the file
        at <outfile>
        """
        logging.debug('downloading %s => %s' % (url, outfile))
        resp = requests.get(url, timeout=30000)
        with file(outfile, 'wb') as f:
            logging.debug('writing file contents')
            f.write(resp.content)

    def _dl_test_zip(self, archid, outdir):
        """Download the test zip for a particular architecture id (<archid>) and
        save it at <outdir>/tests.zip
        """
        logging.debug('downloading test zip for %s to %s' % (archid, outdir))
        srcfile = '%s.%s.tests.zip' % (self.prefix, archid)
        logging.debug('zip source filename: %s' % (srcfile,))
        url = self._build_dl_url(srcfile)
        outfile = os.path.join(self.outdir, outdir, 'tests.zip')
        logging.debug('zip dest filename: %s' % (outfile,))
        self._dl_to_file(url, outfile)

    def _clone_mac(self):
        """Clone the dmg and tests zip for the mac build
        """
        logging.debug('cloning mac build')
        self._ensure_outdir('mac')

        logging.debug('downloading firefox dmg')
        dmg = '%s.mac.dmg' % (self.prefix,)
        logging.debug('dmg source filename: %s' % (dmg,))
        url = self._build_dl_url(dmg)
        outfile = os.path.join(self.outdir, 'mac', 'firefox.dmg')
        logging.debug('dmg dest filename: %s' % (outfile,))
        self._dl_to_file(url, outfile)

        self._dl_test_zip('mac', 'mac')

    def _clone_linux(self):
        """Clone the .tar.bz2 and tests zip for both 32-bit and 64-bit linux
        builds
        """
        logging.debug('cloning linux builds')
        for archid, outdir in (('i686', 'linux32'), ('x86_64', 'linux64')):
            logging.debug('architecture: %s' % (archid,))
            logging.debug('outdir: %s' % (outdir,))
            self._ensure_outdir(outdir)

            logging.debug('downloading firefox tarball')
            srcfile = '%s.linux-%s.tar.bz2' % (self.prefix, archid)
            logging.debug('tarball source filename: %s' % (srcfile,))
            url = self._build_dl_url(srcfile)
            outfile = os.path.join(self.outdir, outdir, 'firefox.tar.bz2')
            logging.debug('tarball dest filename: %s' % (outfile,))
            self._dl_to_file(url, outfile)

            self._dl_test_zip('linux-%s' % (archid,), outdir)

    def _clone_win(self):
        """Clone the firefox zip and tests zip for both 32-bit and 64-bit
        windows builds
        """
        logging.debug('cloning windows builds')
        for archid, outdir in (('32', 'win32'), ('64-x86_64', 'win64')):
            logging.debug('architecture: %s' % (archid,))
            logging.debug('outdir: %s' % (outdir,))
            self._ensure_outdir(outdir)

            logging.debug('downloading firefox zip')
            srcfile = '%s.win%s.zip' % (self.prefix, archid)
            logging.debug('zip source filename: %s' % (srcfile,))
            url = self._build_dl_url(srcfile)
            outfile = os.path.join(self.outdir, outdir, 'firefox.zip')
            logging.debug('zip dest filename: %s' % (outfile,))
            self._dl_to_file(url, outfile)

            self._dl_test_zip('win%s' % (archid,), outdir)

    def _cleanup_old_directories(self):
        """We only keep around so many directories of historical firefoxen. This
        gets rid of ones we don't care about any more
        """
        logging.debug('cleaning up old directories')
        with cwd(self.outroot):
            listing = os.listdir('.')
            logging.debug('candidate files: %s' %  (listing,))

            # We want to make sure that we're not looking at anything that's not
            # a directory that may have somehow gotten into our directory. We
            # also need to ignore dotfiles.
            directories = [l for l in listing
                           if os.path.isdir(l) and not l.startswith('.')]
            logging.debug('directories: %s' % (directories,))

            # Find out when the directories were last modified, and sort the
            # list by that, so we can delete the oldest ones.
            times = [(d, os.stat(d).st_mtime) for d in directories]
            times.sort(key=lambda x: x[1])

            # Now we can figure out which directories to delete!
            delete_us = times[:-self.keep]
            logging.debug('directories to delete: %s' % (delete_us,))

            for d in delete_us:
                logging.debug('removing %s' % (d,))
                shutil.rmtree(d)

    def run(self):
        files = self._gather_filelist()
        self.prefix = self._get_prefix(files)

        # Make sure our output directory exists
        if not os.path.exists(self.outdir):
            logging.debug('creating output directory')
            os.mkdir(self.outdir)

        # Now download all the builds and test zipfiles
        if self.mac:
            self._clone_mac()
        if self.linux:
            self._clone_linux()
        if self.windows:
            self._clone_win()

        self._cleanup_old_directories()

@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config', required=True)
    parser.add_argument('--path', dest='path', required=True)
    parser.add_argument('--nightly', dest='nightly', action='store_true',
            default=False)
    parser.add_argument('--srid', dest='srid', required=True)
    parser.add_argument('--linux', dest='linux', action='store_true',
            default=False)
    parser.add_argument('--mac', dest='mac', action='store_true',
            default=False)
    parser.add_argument('--windows', dest='windows', action='store_true',
            default=False)
    args = parser.parse_args()

    stoneridge._conffile = args.config

    cloner = StoneRidgeCloner(args.path, args.nightly, args.srid, args.linux,
            args.mac, args.windows)
    cloner.run()
