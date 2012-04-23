#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import copy
import glob
import json
import os
import shutil

import stoneridge

class StoneRidgeCollator(object):
    """Takes the data we've collected from our tests and puts it into formats
    the graph server can handle. This is saved into json files for the uploader
    to do its thing with
    """
    def __init__(self):
        self.tmpdir = stoneridge.get_xpcshell_tmp()

    def run(self):
        outfiles = glob.glob(os.path.join(self.tmpdir, '*.out'))
        with file(os.path.join(stoneridge.outdir, 'info.json')) as f:
            info = json.load(f)

        for ofile in outfiles:
            # Make a new copy of the base info
            results = copy.deepcopy(info)
            results['testrun'] = {'date':None, 'suite':None, 'options':{},
                                  'results':{}, 'results_aux':{'totals':[]}}

            # TODO - add network configuration to platform?

            # Figure out the test-specific data
            fname = os.path.basename(ofile)
            suite = fname.split('.')[0]
            finfo = os.stat(ofile)
            results['testrun']['date'] = int(finfo.st_ctime)
            results['testrun']['suite'] = suite

            # Read the raw data
            with file(ofile) as f:
                testinfo = json.load(f)

            # Stick the raw data into the json to be uploaded
            for k, v in testinfo.items():
                if k == 'total':
                    # The graph server calculates totals for us, we just keep
                    # our calculations around for verification in case
                    results['testrun']['results_aux']['totals'].append(v['total'])
                else:
                    if k in results['testrun']['results']:
                        results['testrun']['results'].append(v['total'])
                    else:
                        results['testrun']['results'] = [v['total']]

            # Copy the raw data into our output directory
            shutil.copyfile(ofile, os.path.join(stoneridge.outdir, fname))

            # Write our json results for uploading
            upload_filename = 'upload_%s.json' % (suite,)
            upload_file = os.path.join(stoneridge.outdir, upload_filename)
            with file(upload_file, 'w') as f:
                json.dump(results, f)

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    parser.parse_options()

    collator = StoneRidgeCollator()
    collator.run()
