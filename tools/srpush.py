#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# Lots of these imports try to handle both python 2 and python 3 at the same
# time, which is why the imports here are kind of a mess. Same with the
# raw_input/input thing going on at the bottom. Just trying to make this easy
# for developers to actually use, no matter what their default python is.

import argparse

try:
    import ConfigParser as configparser
except ImportError:
    import configparser

import os

import sys

try:
    import urllib
except ImportError:
    # The stuff we need from urllib
    import urllib.parse as urllib

try:
    import urllib2
except ImportError:
    # The stuff we need from urllib2 is in urllib.request in python 3
    import urllib.request as urllib2

try:
    raw_input
except NameError:
    # input in python 3 is the same as raw_input in python 2
    raw_input = input


def read_config_element(cp, option):
    """Get a piece of info from the config file
    """
    try:
        val = cp.get('srpush', option)
        return val
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        return None


def write_config_element(cp, option, value):
    """Save a piece of info to the in-memory copy of the config file. Changes
    made through this function must be persisted separately.
    """
    if not cp.has_section('srpush'):
        cp.add_section('srpush')
    cp.set('srpush', option, value)


def get_config_from_user(cp, missing_options):
    """Ask the user for config variables missing from their config file, and
    save those variables to the in-memory copy of the config file.
    """
    new_options = {}

    sys.stdout.write('Some configuration options are missing. Please fill them in here.\n')
    for option in missing_options:
        new_options[option] = raw_input('%s: ' % (option,)).strip()
        write_config_element(cp, option, new_options[option])

    return new_options


def srpush(sha, host, ldap, password, netconfigs, operating_systems):
    """Push a build to stoneridge.

    sha - HG sha of the revision to test (first 12 or more characters)
    host - Hostname that receives the push requests
    ldap - Mozilla LDAP username of the builder
    password - Password used to login to the push (NOT the LDAP password)
    netconfigs - List of netconfigs to test against
    operating_systems - List of operating systems to test on

    Returns the srid (Stone Ridge IDentifier) used to keep track of this build
    in the Stone Ridge system (useful for debugging problems).
    """
    url = 'https://%s/srpush' % (host,)

    # ftp.m.o only uses the first 12 characters of the sha
    sha = sha[:12]
    if len(sha) < 12:
        raise Exception('SHA not long enough (must be 12+ characters)')

    password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, url, ldap, password)

    auth_manager = urllib2.HTTPBasicAuthHandler(password_manager)

    opener = urllib2.build_opener(auth_manager)

    urllib2.install_opener(opener)

    srid = '%s-%s' % (ldap, sha)

    post = {'srid': srid,
            'sha': sha,
            'ldap': ldap,
            'netconfig': netconfigs,
            'operating_system': operating_systems}

    req = urllib2.Request(url, data=urllib.urlencode(post, doseq=True))
    handler = urllib2.urlopen(req)

    status = handler.getcode()
    if status != 200:
        raise Exception('Got response %s from server' % (status,))

    return srid


if __name__ == '__main__':
    homedir = os.getenv('HOME')
    if homedir:
        default_config = os.path.join(homedir, '.srpush.ini')
    else:
        default_config = None

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config', default=default_config,
            help='Path to configuration file')
    parser.add_argument('--netconfig', dest='netconfigs',
            choices=('broadband', 'umts', 'gsm', 'all'), required=True,
            help='Netconfigs to run tests against', action='append')
    parser.add_argument('--os', dest='operating_systems',
            choices=('windows', 'mac', 'linux', 'all'), required=True,
            help='Operating systems to run tests on', action='append')
    parser.add_argument('sha', default=None,  help='SHA of try run to push')
    args = parser.parse_args()

    cp = configparser.SafeConfigParser()
    if args.config:
        cp.read(args.config)

    # Try to get the config info out of the config file
    ldap = read_config_element(cp, 'ldap')
    password = read_config_element(cp, 'password')
    host = read_config_element(cp, 'host')

    # See if the user has set the values through environment variables
    ldap = os.getenv('SRPUSH_LDAP', ldap)
    password = os.getenv('SRPUSH_PASSWORD', password)
    host = os.getenv('SRPUSH_HOST', host)

    missing_options = []
    if not ldap:
        missing_options.append('ldap')
    if not password:
        missing_options.append('password')
    if not host:
        missing_options.append('host')

    if missing_options:
        options = {'ldap': ldap, 'password': password, 'host': host}
        options.update(get_config_from_user(cp, missing_options))
        if args.config:
            # Go ahead and save the values off for the user
            with file(args.config, 'w') as f:
                cp.write(f)
        ldap = options['ldap']
        password = options['password']
        host = options['host']

    if 'all' in args.netconfigs:
        netconfigs = ['broadband', 'umts', 'gsm']
    else:
        netconfigs = args.netconfigs

    if 'all' in args.operating_systems:
        operating_systems = ['windows', 'mac', 'linux']
    else:
        operating_systems = args.operating_systems

    srid = srpush(args.sha, host, ldap, password, netconfigs,
            operating_systems)

    sys.stdout.write('Push succeeded. Run ID is %s\n' % (srid,))

    sys.exit(0)
