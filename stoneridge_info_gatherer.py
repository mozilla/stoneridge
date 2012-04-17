#!/usr/bin/env python

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import json
import os
import platform

import stoneridge

class StoneRidgeInfoGatherer(object):
    def run(self):
        info_file = os.path.join(stoneridge.bindir, 'application.ini')
        cp = configparser.SafeConfigParser()
        cp.read([info_file])

        build_info = {}
        build_info['name'] = cp.get('App', 'Name')
        build_info['version'] = cp.get('App', 'Version')
        build_info['revision'] = cp.get('App', 'SourceStamp')
        build_info['branch'] = ''
        build_info['id'] = cp.get('App', 'BuildID')

        machine_info = {}
        machine_info['name'] = platform.node()
        machine_info['os'] = stoneridge.os_name
        machine_info['osversion'] = stoneridge.os_version
        machine_info['platform'] = platform.machine()

        info = {'test_machine':machine_info,
                'test_build':build_info,
                'testrun':{}}

        with file(os.path.join(stoneridge.outdir, 'info.json'), 'w') as f:
            json.dump(info, f)

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    args = parser.parse_arguments()

    info_gatherer = StoneRidgeInfoGatherer()
    info_gatherer.run()
