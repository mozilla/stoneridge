#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

"""This is a script to fix build ids on test runs created before the changes
were made that make the build ids we send be compatible with what the graph
server expects.
"""

import json
import os
import sys

import stoneridge

for fname in sys.argv[1:]:
    try:
        with file(fname) as f:
            info = json.load(f)
    except OSError as e:
        print 'Error opening %s: %s' % (fname, e)
        continue
    except Exception as e:
        print 'Error reading %s: %s' % (fname, e)
        continue

    try:
        os.rename(fname, '%s.orig' % (fname,))
    except Exception as e:
        print 'Error renaming %s: %s' % (fname, e)
        continue

    # See stoneridge_info_gatherer.py for why the buildid is the way it is.
    netconfig = info['test_build']['branch']
    os_name = info['test_machine']['os']
    buildid_suffix = (stoneridge._os_ids[os_name] +
                      stoneridge._netconfig_ids[netconfig])
    original_buildid = info['test_build']['id']
    new_buildid = original_buildid[:14] + buildid_suffix

    info['test_build']['original_buildid'] = original_buildid
    info['test_build']['id'] = new_buildid

    try:
        with file(fname, 'w') as f:
            json.dump(info, f)
    except OSError as e:
        print 'Error opening %s for writing: %s' % (fname, e)
    except Exception as e:
        print 'Error writing %s: %s' %  (fname, e)
