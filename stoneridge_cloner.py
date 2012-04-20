#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import ftplib
import os
import requests
import time

import stoneridge

class StoneRidgeCloner(object):
    """This runs on the central stone ridge server, and downloads releases from
    ftp.m.o to a local directory that is served up to the clients by a plain ol'
    web server. Those clients use stoneridge_downloader.py to get the files they
    need from the central server.
    """
    def __init__(self, host, path, outdir):
        self.host = host
        self.path = path
        self.outroot = os.path.abspath(outdir)
        self.tstamp = time.strftime('%Y%m%d%H%M%S', time.gmtime())
        self.outdir = os.path.join(self.outroot, self.tstamp)
        self.latest = os.path.join(self.outroot, 'latest')

        if not os.path.exists(self.outroot):
            os.mkdir(self.outroot)

        self.prefix = ''

    def _gather_filelist(self):
        """Get the list of files available on our FTP server

        Returns: list of filenames relative to the path on the server
        """
        ftp = ftplib.FTP(self.host)
        ftp.login()
        ftp.cwd(self.path)
        files = ftp.nlst()
        ftp.quit()
        return files

    def _build_dl_url(fname):
        """Create a download (https) URL for a particular file

        Returns: a URL string
        """
        remotefile = os.path.join(self.path, fname)
        return 'https://%s%s' % (self.host, remotefile)

    def _get_stamp_and_prefix(self, files):
        """Get the ID stamp of the latest available build, as well as the
        filename prefix that is common to all the files we'll need to
        download

        Returns: (<id_stamp (string)>, <prefix (string)>)
        """
        stampfile = [f for f in files if f.endswith('.mac.checksums.asc')][0]
        url = self._build_dl_url(stampfile)
        resp = requests.get(url, verify=False)
        return resp.text, stampfile.replace('.mac.checksums.asc', '')

    def _get_last_stamp(self):
        """Get the ID stamp of the latest build we downloaded

        Returns: ID stamp string
        """
        if not os.path.exists(self.latest):
            return None
        lateststamp = os.path.join(self.latest, 'stamp')
        if not os.path.exists(lateststamp):
            return None
        return file(lateststamp).read()

    def _ensure_outdir(self, platform):
        """Ensure the output directory for a platform exists
        """
        if not os.path.exists(self.outdir):
            os.mkdir(self.outdir)
        platdir = os.path.join(self.outdir, platform)
        if not os.path.exists(platdir):
            os.mkdir(platdir)

    def _dl_to_file(self, url, outfile):
        """Download the file at <url> and save it to the file
        at <outfile>
        """
        with file(outfile, 'w') as f:
            resp = requests.get(url, verify=False)
            f.write(resp.txt)

    def _dl_test_zip(self, archid, outdir):
        """Download the test zip for a particular architecture id (<archid>) and
        save it at <outdir>/tests.zip
        """
        srcfile = '%s.%s.tests.zip' % (self.prefix, archid)
        url = self._build_dl_url(srcfile)
        outfile = os.path.join(self.outdir, outdir, 'tests.zip')
        self._dl_to_file(url, outfile)

    def _clone_mac(self):
        """Clone the dmg and tests zip for the mac build
        """
        self._ensure_outdir('mac')

        dmg = '%s.mac.dmg' % (self.prefix,)
        url = self._build_dl_url(dmg)
        outfile = os.path.join(self.outdir, 'mac', 'firefox.dmg')
        self._dl_to_file(url, outfile)

        self._dl_test_zip('mac', 'mac')

    def _clone_linux(self):
        """Clone the .tar.bz2 and tests zip for both 32-bit and 64-bit linux
        builds
        """
        for archid, outdir in (('i686', 'linux32'), ('x86_64', 'linux64')):
            self._ensure_outdir(outdir)

            srcfile = '%s.linux-%s.tar.bz2' % (self.prefix, archid)
            url = self._build_dl_url(srcfile)
            outfile = os.path.join(self.outdir, outdir, 'firefox.tar.bz2')
            self._dl_to_file(url, outfile)

            self._dl_test_zip('linux-%s' % (archid,), outdir)

    def _clone_win(self):
        """Clone the firefox zip and tests zip for both 32-bit and 64-bit
        windows builds
        """
        for archid, outdir in (('32', 'win32'), '64-x86_64', 'win64')):
            self._ensure_outdir(outdir)

            srcfile = '%s.win%s.zip' % (self.prefix, archid)
            url = self._build_dl_url(srcfile)
            outfile = os.path.join(self.outdir, outdir, 'firefox.zip')
            self._dl_to_file(url, outfile)

            self._dl_test_zip('win%s' % (archid,), outdir)

    class cwd(object):
        """A context manager to change our working directory when we enter the
        context, and then change back to the original working directory when we
        exit the context
        """
        def __init__(self, dirname):
            self.newcwd = dirname
            self.oldcwd = os.getcwd()

        def __enter__(self):
            os.chdir(self.newcwd)

        def __exit__(self, *args):
            os.chdir(self.oldcwd)

    def _update_latest(self):
        """Update the "latest" symlink to point to the set of builds
        we just downloaded
        """
        with cwd(self.outroot):
            if os.path.exists('latest'):
                os.unlink('latest')
            target = os.path.basename(self.outdir)
            os.symlink(target, 'latest')

    def run(self):
        files = self._gather_filelist()
        stamp, self.prefix = self._get_stamp_and_prefix(files)
        if stamp == self._get_last_stamp():
            # We've done everything for these builds already, no need to try
            # again
            return

        # Save the new stamp for checking later on
        stampfile = os.path.join(self.outdir, 'stamp')
        with file(stampfile, 'w') as f:
            f.write(stamp)

        # Now download all the builds and test zipfiles
        self._clone_mac()
        self._clone_linux()
        self._clone_win()

        # Finally, update our "latest" pointer to point to this newest clone
        self._update_latest()

@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', dest='host', metavar='HOST',
            default='ftp.mozilla.org', help='Host to clone from')
    parser.add_argument('--path', dest='path', metavar='PATH',
            default='/pub/mozilla.org/firefox/nightly/latest-mozilla-central',
            help='Directory on server to clone from')
    parser.add_argument('--output', dest='outdir', metavar='DIR',
            default='.', help='Where to store cloned files to')

    args = parser.parse_arguments()

    cloner = StoneRidgeCloner(args['host'], args['path'], args['outdir'])
    cloner.run()
