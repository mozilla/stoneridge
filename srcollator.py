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

import logging

class StoneRidgeCollator(object):
    """Takes the data we've collected from our tests and puts it into formats
    the graph server can handle. This is saved into json files for the uploader
    to do its thing with
    """
    def run(self):
        logging.debug('collator running')
        outfiles = glob.glob(os.path.join(stoneridge.xpcoutdir, '*.out'))
        logging.debug('found outfiles %s' % (outfiles,))
        logging.debug('loading info from %s' %
                (os.path.join(stoneridge.outdir, 'info.json'),))
        with file(os.path.join(stoneridge.outdir, 'info.json'), 'rb') as f:
            info = json.load(f)
            logging.debug('loaded info: %s' % (info,))

        for ofile in outfiles:
            logging.debug('processing %s' % (ofile,))
            # Make a new copy of the base info
            results = copy.deepcopy(info)
            del results['date']
            results['testrun'] = {'date':info['date'], 'suite':None, 'options':{}}
            results['results'] = collections.defaultdict(list)
            results['results_aux'] = collections.defaultdict(list)
            logging.debug('initial testrun: %s' % (results['testrun'],))

            # Figure out the test-specific data
            fname = os.path.basename(ofile)
            suite = fname.split('.')[0]
            results['testrun']['suite'] = suite
            logging.debug('suite: %s' % (suite,))

            # Read the raw data
            logging.debug('reading raw data')
            with file(ofile, 'rb') as f:
                testinfo = json.load(f)
                logging.debug('raw testinfo: %s' % (testinfo,))

            # Stick the raw data into the json to be uploaded
            logging.debug('processing raw data')
            for k, vlist in testinfo.items():
                logging.debug('k: %s, vlist: %s' % (k, vlist))
                for v in vlist:
                    logging.debug('v: %s' % (v,))
                    if k == 'total':
                        logging.debug('appending total %s' % (v['total'],))
                        # The graph server calculates totals for us, we just keep
                        # our calculations around for verification in case
                        results['results_aux']['totals'].append(v['total'])
                    else:
                        logging.debug('appending %s total %s' % (k, v['total']))
                        results['results'][k].append(v['total'])

                        for s in ('start', 'stop'):
                            key = '%s_%s' % (k, s)
                            logging.debug('appending %s %s stamp %s' %
                                    (k, s, v[s]))
                            results['results_aux'][key].append(v[s])

            # Turn our defaultdicts into regular dicts for jsonification
            results['results'] = dict(results['results'])
            results['results_aux'] = dict(results['results_aux'])
            logging.debug('results: %s' % (results['results'],))
            logging.debug('aux results: %s' % (results['results_aux'],))

            # Copy the raw data into our output directory
            logging.debug('copying raw data to archivable directory')
            shutil.copyfile(ofile, os.path.join(stoneridge.outdir, fname))

            # Write our json results for uploading
            upload_filename = 'upload_%s.json' % (suite,)
            logging.debug('upload filename: %s' % (upload_filename,))
            upload_file = os.path.join(stoneridge.outdir, upload_filename)
            with file(upload_file, 'wb') as f:
                logging.debug('jsonifying %s' % (results,))
                json.dump(results, f)

@stoneridge.main
def main():
    parser = stoneridge.ArgumentParser()
    parser.parse_args()

    collator = StoneRidgeCollator()
    collator.run()
