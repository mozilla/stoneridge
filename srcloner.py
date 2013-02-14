#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import ftplib
import logging
import os
import requests
import shutil
import sys
import tempfile

import stoneridge


LINUX_SUBDIRS = ('try-linux', 'try-linux64')
MAC_SUBDIRS = ('try-macosx64',) # There is only one OS X build
WINDOWS_SUBDIRS = ('try-win32',) # win64 is unsupported, so ignore it for now


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
    def __init__(self, nightly, srid, operating_systems, netconfigs,
            ldap, sha, attempt):
        self.host = stoneridge.get_config('cloner', 'host')
        self.nightly = nightly
        self.outroot = stoneridge.get_config('cloner', 'output')
        self.srid = srid
        self.outdir = os.path.join(self.outroot, srid)
        self.keep = stoneridge.get_config_int('cloner', 'keep', default=50)
        self.max_attempts = stoneridge.get_config_int('cloner', 'attempts')
        self.operating_systems = operating_systems
        self.netconfigs = netconfigs
        self.ldap = ldap
        self.sha = sha
        self.attempt = attempt

        if not os.path.exists(self.outroot):
            os.mkdir(self.outroot)

        root = stoneridge.get_config('cloner', 'root')
        if nightly:
            self.path = '/'.join([root, 'nightly', 'latest-mozilla-central'])
        else:
            self.path = '/'.join([root, 'try-builds', '%s-%s' % (ldap, sha)])

        logging.debug('host: %s' % (self.host,))
        logging.debug('path: %s' % (self.path,))
        logging.debug('nightly: %s' % (self.nightly,))
        logging.debug('srid: %s' % (self.srid,))
        logging.debug('output root: %s' % (self.outroot,))
        logging.debug('output directory: %s' % (self.outdir,))
        logging.debug('keep history: %s' % (self.keep,))
        logging.debug('max attempts: %s' % (self.max_attempts,))
        logging.debug('operating systems: %s' % (self.operating_systems,))
        logging.debug('netconfigs: %s' % (self.netconfigs,))
        logging.debug('ldap: %s' % (self.ldap,))
        logging.debug('sha: %s' % (self.sha,))
        logging.debug('attempt: %s' % (self.attempt,))

        self.prefix = ''

    def _gather_filelist(self, path):
        """Get the list of files available on our FTP server

        Returns: list of filenames relative to the path on the server
        """
        logging.debug('gathering files from ftp server')

        try:
            ftp = ftplib.FTP(self.host)
            ftp.login()
            ftp.cwd(path)
            files = ftp.nlst()
            ftp.quit()
        except:
            # We blanket-catch exceptions here, because we want the error
            # handling in the top level to take precedence for ANY problem that
            # happens while listing the directory. Logging helps us track down
            # unexpected errors that may occur.
            logging.exception('Unable to list files in %s' % (path,))
            return []

        logging.debug('files in %s: %s' % (path, files))
        return files

    def _build_dl_url(self, try_subdir, fname):
        """Create a download (https) URL for a particular file

        Returns: a URL string
        """
        logging.debug('creating download url for %s' % (fname,))
        remotefile = self.path
        if not self.nightly:
            remotefile = '/'.join([remotefile, try_subdir])
        remotefile = '/'.join([remotefile, fname])
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
        prefixfile = [f for f in files if f.endswith('.checksums.asc')][-1]
        prefix = prefixfile.replace('.checksums.asc', '')
        prefix = prefix.rsplit('.', 1)[0] # Strip off the platform information
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

    def _dl_test_zip(self, try_subdir, archid, outdir):
        """Download the test zip for a particular architecture id (<archid>) and
        save it at <outdir>/tests.zip
        """
        logging.debug('downloading test zip for %s to %s' % (archid, outdir))
        srcfile = '%s.%s.tests.zip' % (self.prefix, archid)
        logging.debug('zip source filename: %s' % (srcfile,))
        url = self._build_dl_url(try_subdir, srcfile)
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
        url = self._build_dl_url(MAC_SUBDIRS[0], dmg)
        outfile = os.path.join(self.outdir, 'mac', 'firefox.dmg')
        logging.debug('dmg dest filename: %s' % (outfile,))
        self._dl_to_file(url, outfile)

        self._dl_test_zip(MAC_SUBDIRS[0], 'mac', 'mac')

    def _clone_linux(self):
        """Clone the .tar.bz2 and tests zip for both 32-bit and 64-bit linux
        builds
        """
        logging.debug('cloning linux builds')
        archids = ('i686', 'x86_64')
        outdirs = ('linux32', 'linux64')
        for archid, outdir, subdir in zip(archids, outdirs, LINUX_SUBDIRS):
            logging.debug('architecture: %s' % (archid,))
            logging.debug('outdir: %s' % (outdir,))
            self._ensure_outdir(outdir)

            logging.debug('downloading firefox tarball')
            srcfile = '%s.linux-%s.tar.bz2' % (self.prefix, archid)
            logging.debug('tarball source filename: %s' % (srcfile,))
            url = self._build_dl_url(subdir, srcfile)
            outfile = os.path.join(self.outdir, outdir, 'firefox.tar.bz2')
            logging.debug('tarball dest filename: %s' % (outfile,))
            self._dl_to_file(url, outfile)

            self._dl_test_zip(subdir, 'linux-%s' % (archid,), outdir)

    def _clone_win(self):
        """Clone the firefox zip and tests zip for both 32-bit and 64-bit
        windows builds
        """
        logging.debug('cloning windows build')
        self._ensure_outdir('win32')

        logging.debug('downloading firefox zip')
        srcfile = '%s.win32.zip' % (self.prefix,)
        logging.debug('zip source filename: %s' % (srcfile,))
        url = self._build_dl_url(WINDOWS_SUBDIRS[0], srcfile)
        outfile = os.path.join(self.outdir, 'win32', 'firefox.zip')
        logging.debug('zip dest filename: %s' % (outfile,))
        self._dl_to_file(url, outfile)

        self._dl_test_zip(WINDOWS_SUBDIRS[0], 'win32', 'win32')

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

    def defer(self):
        args = ['srdeferrer.py',
                '--srid', self.srid,
                '--config', stoneridge.get_config_file(),
                '--log', '/dev/null',
                '--pidfile', tempfile.mktemp(),
                '--attempt', self.attempt + 1]

        if self.nightly:
            args.append('--nightly')
        else:
            args.extend(['--ldap', self.ldap])
            args.extend(['--sha', self.sha])
            for ops in self.operating_systems:
                args.append('--%s' % (ops,))
            for nc in self.netconfigs:
                args.append('--%s' % (nc,))

        stoneridge.run_process(*args)

        sys.exit(0)

    def exit_and_maybe_defer(self, deferred_message):
        next_attempt = self.attempt + 1
        if next_attempt > self.max_attempts:
            logging.error('Unable to get build results for %s after %s '
                    'attempts. Cancelling run.' %
                    (self.srid, self.max_attempts))
        else:
            self.defer()
            logging.debug(deferred_message)
        sys.exit(1)

    def run(self):
        files = self._gather_filelist(self.path)
        if not self.nightly:
            # For some ungodly reason, try builds have a different directory
            # structure than nightly builds, so we have to handle them
            # differently. Instead of all output being at the same level,
            # they are separated out by platform for try builds. Le sigh.
            subdirs = []
            dist_files = None
            if 'linux' in self.operating_systems:
                subdirs.extend(LINUX_SUBDIRS)
            if 'mac' in self.operating_systems:
                subdirs.extend(MAC_SUBDIRS)
            if 'windows' in self.operating_systems:
                subdirs.extend(WINDOWS_SUBDIRS)

            # Be reasonably sure the try run is complete, such that everything
            # is ready for us to download.
            for d in subdirs:
                if d not in files:
                    self.exit_and_maybe_defer(
                            'Run %s not available: retry later' % (d,))

            dist_path = '/'.join([self.path, subdirs[0]])
            dist_files = self._gather_filelist(dist_path)

            if not dist_files:
                # We didn't get any files listed, but we should have. Just drop
                # this run on the floor
                logging.error('No files found! Dropping srid %s' % (self.srid,))
                sys.exit(1)

            files = dist_files

        if not files:
            self.exit_and_maybe_defer(
                    'No files found for %s: retry later' % (self.srid,))

        self.prefix = self._get_prefix(files)

        # Make sure our output directory exists
        if not os.path.exists(self.outdir):
            logging.debug('creating output directory')
            os.mkdir(self.outdir)

        # Now download all the builds and test zipfiles
        if self.nightly or 'mac' in self.operating_systems:
            self._clone_mac()
        if self.nightly or 'linux' in self.operating_systems:
            self._clone_linux()
        if self.nightly or 'windows' in self.operating_systems:
            self._clone_win()

        self._cleanup_old_directories()


@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    parser.add_argument('--nightly', dest='nightly', action='store_true',
            default=False)
    parser.add_argument('--srid', dest='srid', required=True)
    for ops in stoneridge.OPERATING_SYSTEMS:
        parser.add_argument('--%s' % (ops,), dest='operating_systems',
                action='append_const', const=ops, default=[])
    for nc in stoneridge.NETCONFIGS:
        parser.add_argument('--%s' % (nc,), dest='netconfigs',
                action='append_const', const=nc, default=[])
    parser.add_argument('--attempt', dest='attempt', required=True, type=int)
    parser.add_argument('--ldap', dest='ldap', default='')
    parser.add_argument('--sha', dest='sha', default='')
    args = parser.parse_args()

    cloner = StoneRidgeCloner(args.nightly, args.srid, args.operating_systems,
            args.netconfigs, args.ldap, args.sha, args.attempt)
    cloner.run()
