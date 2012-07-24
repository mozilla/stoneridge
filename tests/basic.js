/**
 * A simple request test.  This measures the time between creation of the request channel
 * and first delivery of the data and time needed to deliver all data expected plus an overall
 * time to complete the load.  The request must succeed otherwise the test fails.
 */

var startTime = null;
var firstDataTime = null;
var endTime = null;

listener = {
  onStartRequest: function() {
  },

  onDataAvailable: function() {
    if (!firstDataTime) {
       firstDataTime = new Date();
       firstDataTime = firstDataTime.getMilliseconds();
    }
  },

  onStopRequest: function(request, context, status) {
    //do_check(status === 0, "request to '" + request.name + "' failed");

    endTime = new Date();
    endTime = endTime.getMilliseconds();

    do_write_result("latency", startTime, firstDataTime);
    do_write_result("data_delivery", firstDataTime, endTime);
    do_write_result("total", startTime, endTime);

    do_test_finish();
  }
};

function run_test() // The entry point
{
  startTime = new Date();
  startTime = startTime.getMilliseconds();
  var channel = make_channel("http://example.org/");
  channel.asyncOpen(listener, null);
}
