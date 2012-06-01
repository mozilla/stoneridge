#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

import collections
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
    def run(self):
        outfiles = glob.glob(os.path.join(stoneridge.xpcoutdir, '*.out'))
        with file(os.path.join(stoneridge.outdir, 'info.json'), 'rb') as f:
            info = json.load(f)

        for ofile in outfiles:
            # Make a new copy of the base info
            results = copy.deepcopy(info)
            results['testrun'] = {'date':None, 'suite':None, 'options':{}}
            results['results'] = collections.defaultdict(list)
            results['results_aux'] = collections.defaultdict(list)

            # Figure out the test-specific data
            fname = os.path.basename(ofile)
            suite = fname.split('.')[0]
            finfo = os.stat(ofile)
            results['testrun']['date'] = int(finfo.st_ctime)
            results['testrun']['suite'] = suite

            # Read the raw data
            with file(ofile, 'rb') as f:
                testinfo = json.load(f)

            # Stick the raw data into the json to be uploaded
            for k, vlist in testinfo.items():
                for v in vlist:
                    if k == 'total':
                        # The graph server calculates totals for us, we just keep
                        # our calculations around for verification in case
                        results['results_aux']['totals'].append(v['total'])
                    else:
                        results['results'][k].append(v['total'])

                        for s in ('start', 'stop'):
                            key = '%s_%s' % (k, s)
                            results['results_aux'][key].append(v[s])

            # Turn our defaultdicts into regular dicts for jsonification
            results['results'] = dict(results['results'])
            results['results_aux'] = dict(results['results_aux'])

            # Copy the raw data into our output directory
            shutil.copyfile(ofile, os.path.join(stoneridge.outdir, fname))

            # Write our json results for uploading
            upload_filename = 'upload_%s.json' % (suite,)
            upload_file = os.path.join(stoneridge.outdir, upload_filename)
            with file(upload_file, 'wb') as f:
                json.dump(results, f)

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    parser.parse_args()

    collator = StoneRidgeCollator()
    collator.run()
