#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import argparse

try:
    import ConfigParser as configparser
except ImportError:
    import configparser

import os

try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

try:
    raw_input
    def print(*args):
        print map(str, args)
except NameError:
    raw_input = input


def read_config_element(cp, option):
    try:
        val = cp.get('srpush', option)
        return val
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        return None


def write_config_element(cp, option, value):
    if not cp.has_section('srpush'):
        cp.add_section('srpush')
    cp.set('srpush', option, value)


def get_config_from_user(cp, missing_options):
    new_options = {}

    print('Some configuration options are missing. Please fill them in here.')
    for option in missing_options:
        new_options[option] = raw_input('%s: ' % (option,)).strip()
        write_config_element(cp, option, new_options[option])

    return new_options


def srpush(sha, host, ldap, password):
    # TODO: still a lot of work to happen in this function. Generate srid,
    # format the post data correctly, return the srid, possibly some other
    # things that I'm forgetting in my rush.

    password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, url, ldap, password)

    auth_manager = urllib2.HTTPBasicAuthHandler(password_manager)

    opener = urllib2.build_opener(auth_manager)

    urllib2.install_opener(opener)

    url = 'https://%s/srpush' % (host,)
    req = urllib2.Request(url, data=post_data)
    handler = urllib2.urlopen(req)


if __name__ == '__main__':
    homedir = os.getenv('HOME')
    if homedir:
        default_config = os.path.join(homedir, '.srpush.ini')
    else:
        default_config = None

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', dest='config', default=default_config,
            help='Path to configuration file')
    parser.add_argument('sha', dest='sha', default=None, required=True,
            help='SHA of try run to push')
    args = parser.parse_args()

    cp = configparser.SafeConfigParser()
    if parser.config:
        cp.read(parser.config)

    ldap = read_config_element(cp, 'ldap')
    password = read_config_element(cp, 'password')
    host = read_config_element(cp, 'host')

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
        if parser.config:
            with file(parser.config, 'w') as f:
                cp.write(f)
        ldap = options['ldap']
        password = options['password']
        host = options['host']

    srpush(args.sha, host, ldap, password)

    sys.exit(0)
