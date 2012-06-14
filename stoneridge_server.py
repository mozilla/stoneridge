import argparse
import BaseHTTPServer
import cgi
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
        rootdir = stoneridge.get_config('server', 'uploads')
        now = int(time.time())
        idx = 0

        post = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                         'CONTENT_TYPE':self.headers['Content-Type']})

        for k in post.keys():
            pfx = '%s_%s_' % (now, idx)
            idx += 1
            v = post[k].value

            fd, name = tempfile.mkstemp(dir=rootdir, prefix=pfx, suffix='.json')
            os.write(fd, v)
            os.close(fd)

        self.send_response(200)

    def translate_path(self, path):
        """Override the base translate_path to get something with a configurable
        root
        """
        rootdir = stoneridge.get_config('server', 'downloads')
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        path = posixpath.normpath(urllib.unquote(path))
        words = [w for w in path.split('/') if w]
        path = rootdir
        for w in words:
            path = os.path.join(path, w)
        return path

@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config', required=True)
    args = parser.parse_args()

    stoneridge._conffile = args.config

    httpd = BaseHTTPServer.HTTPServer(('127.0.0.1', 8080), SRUploadHandler)
    httpd.serve_forever()
