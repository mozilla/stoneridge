import argparse
import BaseHTTPServer
import cgi
import os
import tempfile
import time

import stoneridge

class SRUploadHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_POST(self):
        rootdir = stoneridge.get_config('server', 'directory')
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

@stoneridge.main
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config', required=True)
    args = parser.parse_args()

    stoneridge._conffile = args.config

    httpd = BaseHTTPServer.HTTPServer(('127.0.0.1', 8080), SRUploadHandler)
    httpd.serve_forever()
