function run_test()
{
  startTime = new Date();
  endTime = new Date(startTime.valueOf() + 100);
  do_write_result("junk", startTime, endTime);
  do_test_finish();
}
