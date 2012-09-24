#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import ConfigParser
import json
import os
import platform
import time

import stoneridge

class StoneRidgeInfoGatherer(object):
    """Gathers information about the platform stone ridge is running on as well
    as the build that stone ridge is being run against
    """
    def run(self):
        info_file = os.path.join(stoneridge.bindir, 'application.ini')
        cp = ConfigParser.SafeConfigParser()
        cp.read([info_file])

        build_info = {}
        build_info['name'] = cp.get('App', 'Name')
        build_info['version'] = cp.get('App', 'Version')
        build_info['revision'] = cp.get('App', 'SourceStamp')
        build_info['branch'] = stoneridge.current_netconfig

        # Due to the way the graph server works, we need to create a unique
        # build id for each build/netconfig combination. We also want to keep
        # the unmodified build ID around for posterity.
        build_info['original_buildid'] = cp.get('App', 'BuildID')
        # Cut off the century and the seconds from the date in the build id, as
        # they are relatively useless bits of information.
        buildid_base = build_info['original_buildid'][2:-2]
        # Build ID is limited to 16 characters in the receiving database.
        build_info['id'] = (buildid_base + stoneridge.current_netconfig)[:16]

        machine_info = {}
        machine_info['name'] = platform.node()
        machine_info['os'] = stoneridge.os_name
        machine_info['osversion'] = stoneridge.os_version
        machine_info['platform'] = platform.machine()

        info = {'test_machine':machine_info,
                'test_build':build_info,
                'testrun':{},
                'date':int(time.time())}

        if not os.path.exists(stoneridge.outdir):
            os.mkdir(stoneridge.outdir)

        with file(os.path.join(stoneridge.outdir, 'info.json'), 'wb') as f:
            json.dump(info, f)

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    args = parser.parse_args()

    info_gatherer = StoneRidgeInfoGatherer()
    info_gatherer.run()
