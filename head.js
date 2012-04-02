/*
 * This Source Code Form is subject to the terms of the Mozilla Public License,
 * v. 2.0. If a copy of the MPL was not distributed with this file, You can
 * obtain one at http://mozilla.org/MPL/2.0/.
 *
 * This file defines the commonly-used functionality needed by a stone ridge
 * test suite. This must be run under xpcshell running in JS v1.8 mode.
 */

var OUT_FILE = null;

var Cc = Components.classes;
var Ci = Components.interfaces;
var Cr = Components.results;

/*
 * Write some JSON object to the file named in OUT_FILE.
 */
function writeTestLog(json_obj) {
  var ofile = Cc["@mozilla.org/file/directory_service;1"].
              getService(Ci.nsIProperties).
              get("CurWorkD", Ci.nsILocalFile);

  // Walk up to the root
  while (ofile.parent) {
    ofile = ofile.parent;
  }

  // And use the file determined by our caller
  ofile.append(OUT_FILE);

  // Now get an output stream for our file
  var ostream = Cc["@mozilla.org/network/file-output-stream;1"].
                createInstance(Ci.nsIFileOutputStream);
  ostream.init(ofile, -1, -1, 0);

  var jstring = JSON.stringify(json_obj);
  ostream.write(jstring, jstring.length);
  ostream.close();
}

/*
 * The main entry point for all stone ridge tests
 */
function stoneRidge(output_filename) {
  OUT_FILE = output_filename;
  run_test();
}
