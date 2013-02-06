#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import json

import requests

import stoneridge


@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    parser.parse_args()

    root = stoneridge.get_config('enqueuer', 'root')
    username = stoneridge.get_config('enqueuer', 'username')
    password = stoneridge.get_config('enqueuer', 'password')

    res = requests.get(root + '/list_unhandled', auth=(username, password))
    queue = json.loads(res.text)

    for entry in queue:
        stoneridge.enqueue(nightly=False, ldap=entry['ldap'], sha=entry['sha'],
                netconfigs=entry['netconfigs'],
                operating_systems=entry['operating_systems'],
                srid=entry['srid'])
        requests.post(root + '/mark_handled', data={'id': entry['pushid']},
                auth=(username, password))
