/*
 * This Source Code Form is subject to the terms of the Mozilla Public License,
 * v. 2.0. If a copy of the MPL was not distributed with this file, You can
 * obtain one at http://mozilla.org/MPL/2.0/.
 *
 * This file defines the commonly-used functionality needed by a stone ridge
 * test suite. This must be run under xpcshell running in JS v1.8 mode.
 */

/*jshint curly:true, indent:4, latedef:true, undef:true, unused:true,
  trailing:true, es5:true, esnext:true*/
/*global Components:true*/

var STONERIDGE_RESULTS = null;

/*
 * Store some results for writing once we're all done
 */
function do_write_result(key, start, stop) {
    var startms;
    var stopms;

    if (STONERIDGE_RESULTS === null) {
        STONERIDGE_RESULTS = {};
    }

    if (start instanceof Date) {
        startms = start.valueOf();
    } else {
        startms = start;
    }

    if (stop instanceof Date) {
        stopms = stop.valueOf();
    } else {
        stopms = stop;
    }

    var val = {'start': startms, 'stop': stopms, 'total': stopms - startms};

    if (STONERIDGE_RESULTS.hasOwnProperty(key)) {
        STONERIDGE_RESULTS[key].push(val);
    } else {
        STONERIDGE_RESULTS[key] = [val];
    }
}

function do_save_results(output_file) {
    var cc = Components.classes;
    var ci = Components.interfaces;

    // Create a file pointing to our output file
    var ofile = cc["@mozilla.org/file/local;1"].createInstance(ci.nsILocalFile);
    ofile.initWithPath(output_file);

    // Now get an output stream for our file
    var ostream = cc["@mozilla.org/network/file-output-stream;1"].
                  createInstance(ci.nsIFileOutputStream);
    ostream.init(ofile, -1, -1, 0);

    var jstring = JSON.stringify(STONERIDGE_RESULTS);
    ostream.write(jstring, jstring.length);
    ostream.close();
}
