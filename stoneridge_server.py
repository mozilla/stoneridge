import argparse
import BaseHTTPServer
import cgi
import daemonize
import logging
import os
import posixpath
import SimpleHTTPServer
import tempfile
import time
import urllib

import stoneridge

class SRUploadHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_POST(self):
        """Handle getting uploaded results from the clients
        """
        logging.debug('Handling request from %s' % (self.client_address,))
        logging.debug('Path: %s' % (self.path,))
        rootdir = stoneridge.get_config('server', 'uploads')
        now = int(time.time())
        idx = 0

        post = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                         'CONTENT_TYPE':self.headers['Content-Type']})

        for k in post.keys():
            v = post[k].value
            logging.debug('Processing post variable %s' % (k,))
            logging.debug('%s value = %s' % (k, v))
            if len(v) < 10:
                # Stupid check to filter out junk data that gets submitted from
                # time to time, until we can figure out why said junk data gets
                # submitted
                logging.debug('Skipping invalid json value')
                continue
            pfx = '%s_%s_' % (now, idx)
            idx += 1

            fd, name = tempfile.mkstemp(dir=rootdir, prefix=pfx, suffix='.json')
            os.write(fd, v)
            os.close(fd)

        self.send_response(200)

    def translate_path(self, path):
        """Override the base translate_path to get something with a configurable
        root
        """
        logging.debug('Translating path %s' % (path,))
        rootdir = stoneridge.get_config('server', 'downloads')
        path = path.split('?', 1)[0]
        logging.debug('Without query string: %s' % (path,))
        path = path.split('#', 1)[0]
        logging.debug('Without fragment: %s' % (path,))
        path = posixpath.normpath(urllib.unquote(path))
        logging.debug('Normalized path: %s' % (path,))
        words = [w for w in path.split('/') if w]
        logging.debug('Non-empty path components: %s' % (words,))
        path = rootdir
        logging.debug('Root of translated path: %s' % (path,))
        for w in words:
            path = os.path.join(path, w)
        logging.debug('Translated path: %s' % (path,))
        return path

def daemon():
    httpd = BaseHTTPServer.HTTPServer(('0.0.0.0', 8080), SRUploadHandler)
    httpd.serve_forever()

def do_exit(parser, msg):
    parser.print_usage()
    parser.exit(2, msg % (parser.prog,))

def do_mutex_exit(parser, arg):
    msg = '%%s: error: argument %s: not allowed with argument --nodaemon\n'
    do_exit(parser, msg % (arg,))

def do_missing_exit(parser, arg):
    msg = '%%s: error: argument %s is required\n'
    do_exit(parser, msg % (arg,))

@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config', required=True)
    parser.add_argument('--nodaemon', dest='nodaemon', action='store_true')
    parser.add_argument('--pidfile', dest='pidfile')
    parser.add_argument('--log', dest='log')
    args = parser.parse_args()

    stoneridge._conffile = args.config

    if args.nodaemon:
        if args.pidfile:
            do_mutex_exit(parser, '--pidfile')
        if args.log:
            do_mutex_exit(parser, '--log')
        daemon()
        sys.exit(0)

    if not args.pidfile:
        do_missing_exit(parser, '--pidfile')
    if not args.log:
        do_missing_exit(parser, '--log')

    daemonize.start(daemon, args.pidfile, args.log, debug=True)
