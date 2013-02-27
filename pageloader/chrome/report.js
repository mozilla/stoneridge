/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

// given an array of strings, finds the longest common prefix
function findCommonPrefixLength(strs) {
  if (strs.length < 2)
    return 0;

  var len = 0;
  do {
    var newlen = len + 1;
    var newprefix = null;
    var failed = false;
    for (var i = 0; i < strs.length; i++) {
      if (newlen > strs[i].length) {
        failed = true;
        break;
      }

      var s = strs[i].substr(0, newlen);
      if (newprefix === null) {
        newprefix = s;
      } else if (newprefix != s) {
        failed = true;
        break;
      }
    }

    if (failed)
      break;

    len++;
  } while (true);
  return len;
}

// Constructor
function Report() {
  this.timeVals = {};
  this.totalCCTime = 0;
  this.showTotalCCTime = false;
}

Report.prototype.pageNames = function() {
  var retval = [];
  for (var page in this.timeVals) {
    retval.push(page);
  }
  return retval;
};

// NWGH: This needs to change to return the json type thing we expect in SR
Report.prototype.getReport = function() {

  var report;
  var pages = this.pageNames();
  var prefixLen = findCommonPrefixLength(pages);

  report = "__start_tp_report\n";
  report += "_x_x_mozilla_page_load\n";
  report += "_x_x_mozilla_page_load_details\n";
  report += "|i|pagename|runs|\n";

  for (var i=0; i < pages.length; i++) {
    report += '|'+
      i + ';'+
      pages[i].substr(prefixLen) + ';'+
      this.timeVals[pages[i]].join(";") +
      "\n";
  }
  report += "__end_tp_report\n";

  if (this.showTotalCCTime) {
    report += "__start_cc_report\n";
    report += "_x_x_mozilla_cycle_collect," + this.totalCCTime + "\n";
    report += "__end_cc_report\n";
  }
  var now = (new Date()).getTime();
  report += "__startTimestamp" + now + "__endTimestamp\n"; //timestamp for determning shutdown time, used by talos

  return report;
};

Report.prototype.recordTime = function(pageName, ms) {
  if (this.timeVals[pageName] === undefined) {
    this.timeVals[pageName] = [];
  }
  this.timeVals[pageName].push(ms);
};

Report.prototype.recordCCTime = function(ms) {
  this.totalCCTime += ms;
  this.showTotalCCTime = true;
};
