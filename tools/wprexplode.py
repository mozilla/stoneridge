import argparse
import hashlib
import os
import sys
import urlparse

import httparchive

VHOST_CONFIG = """<VirtualHost *:80>
    RewriteEngine On
    RewriteOptions Inherit
    ServerName %(host)s
    DocumentRoot %(toplevel)s/%(host)s
</VirtualHost>
"""


def explode_archive(wprfile, archiveroot):
    """Explode a HTTP Archive into its component pages. For a file named
    foo.har, the exploded http archive will be put in a directory named foo
    with the same parent directory as foo.har. Beneath that will be directories
    named for each host in the archive, each containing the full paths to the
    files from that host massaged to be consumed by apache's mod_asis
    """
    # Make our directory to explode the HAR into
    hardir = os.path.splitext(os.path.basename(wprfile))[0]
    toplevel = os.path.join(archiveroot, hardir)
    os.mkdir(toplevel)

    # Keep track of the hosts in here so we can make http conf for them
    hosts = set()

    # Load our HAR file
    har = httparchive.HttpArchive.Load(wprfile)

    for request in har.get_requests():
        # Keep track of this host
        hosts.add(request.host)

        # Figure out where to put this file
        hostdir = os.path.join(toplevel, request.host)
        url = urlparse.urlparse(request.path)

        # Make sure our destination directory exists
        if not os.path.exists(hostdir):
            os.makedirs(hostdir)

        # Make sure we have a file name
        name = url.path + url.params
        if not name:
            name = '/'

        if url.query:
            name = name + '?' + url.query

        sys.stdout.write('Translating %s "%s" -> ' % (request.host, name))

        # Hash everything up
        name = hashlib.sha1(name).hexdigest()

        # Make apache recognize the file as an "asis" file
        name += '.asis'

        sys.stdout.write('"%s"\n' % (name,))

        # Write our data out
        fname = os.path.join(hostdir, name)
        response = har[request]
        if os.path.exists(fname):
            sys.stderr.write('WARNING: Replacing %s%s\n' % (request.host,
                                                            url.path))
        with file(fname, 'w') as f:
            # Special "Status:" header for apache to set the HTTP status
            f.write('Status: %s %s\n' % (response.status, response.reason))

            # The rest of the headers are pretty standard
            for k, v in sorted(response.headers):
                if k.lower() == 'transfer-encoding' and v.lower() == 'chunked':
                    # Don't use chunked transfer-encoding, it breaks things
                    continue
                f.write('%s: %s\n' % (k, v))

            # Apache expects a blank line to separate headers and content
            f.write('\n')

            # This should give us the raw file (compressed if appropriate)
            f.write(''.join(response.response_data))

    # Now write out the httpd configuration specific to this archive
    httpd_conf_name = '%s.conf' % (hardir,)
    httpd_conf = os.path.join(archiveroot, httpd_conf_name)
    with file(httpd_conf, 'w') as f:
        for host in hosts:
            f.write(VHOST_CONFIG % {'host': host, 'toplevel': toplevel})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', dest='archive', required=True)
    parser.add_argument('--outdir', dest='outdir', required=True)
    args = parser.parse_args()

    explode_archive(args.archive, args.outdir)
