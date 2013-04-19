# General Overview
Stone Ridge is a combination of dedicated hardware and software to test
networking performance in Firefox under real-world(-ish) conditions. We
simulate three different kinds of networks (called "netconfigs").

1. Broadband similar to what those of us in the US have at home ("broadband")
2. Cellular traffic similar to what those of us in the US have ("umts")
3. Cellular traffic similar to what you might find in less developed parts of the world ("gsm")

We are able to test against each of these netconfigs on all of our Tier-1
desktop platforms (Mac OS X 10.8, Windows 7, and Linux (CentOS 6)).

The testbed is made up of 6 machines: 4 linux machines, 1 mac mini, and 1
windows machine. These machines are:

stone-ridge-linux1.dmz.scl3.mozilla.com - Stone Ridge Master and server for broadband netconfig
stone-ridge-linux2.dmz.scl3.mozilla.com - Server for umts netconfig
stone-ridge-linux3.dmz.scl3.mozilla.com - Server for gsm netconfig
stone-ridge-linux4.dmz.scl3.mozilla.com - Linux client machine
stone-ridge-mac1.dmz.scl3.mozilla.com - Mac OS X client machine
stone-ridge-win1.dmz.scl3.mozilla.com - Windows 7 client machine

None of these machines use any virtualization because we can't risk the sharing
of resources that comes with virtualization that could affect the test numbers.

# Machine Roles

## Master
stone-ridge-linux1.dmz.scl3.mozilla.com

This is the only machine that needs to talk to anything outside the stone
ridge testbed. Its main functions are

* Download builds from ftp.m.o
* Serve those builds to the clients
* Receive stone ridge push requests for "try"-like runs
* Schedule nightly stone ridge runs
* Tell other machines what tests to run and when
* Receive results from test runs and forward them on to datazilla.m.o
* Email results from "try"-like runs to the user that requested them

The queue of stone ridge runs that are waiting or being processed is stored in
a RabbitMQ instance running on the master.

### Special Windows Considerations
Since windows is a pain in the you-know-where, it is prone to losing its
connection to the RabbitMQ instance running on the master. To mitigate this,
I have written a web-based "mq" that is entirely for jobs that need to run on
the windows client. Instead of talking to RabbitMQ directly, the windows client
periodically asks the webmq if there are any jobs for it, and runs them if so.
There is a special process running on the master that takes messages destined
for windows out of RabbitMQ and places them into an sqlite database used by the
webmq, which then serves them to the windows client.

### Processes running on the master

#### rabbitmq
This is the message queue server that everything talks to to find out what it
needs to do

#### nginx
This is the server that is used to serve builds of firefox to the clients

#### srmaster
This is the process that takes requests to run stone ridge tests (either
the nightly cron job or a "pushed" test against a try build) and makes them
ready to run. It does this by running srcloner to do the downloading of builds.
Once the builds have been successfully downloaded, this process places messages
in each of the servers' queues to let them know that they need to schedule tests
to be run against their netconfig.

#### srcloner
These are processes that are used to download builds from ftp.m.o. If the
download succeeds, it exits cleanly so the master knows the build is ready
to be used for testing. Otherwise, it will exit uncleanly so the master knows
to throw away this attempt for the build. If it's been less than a day since the
first time we tried to download this build, it will kick off a deferrer process
(see below) before exiting.

#### srdeferrer
These are processes that sleep for a while (to give try builds a chance to
finish) and then re-insert them as "new" runs in the master.

#### srmqproxy
This is the process that takes messages bound for the windows client out of
RabbitMQ and puts them into a sqlite database.

#### srwebmq
This is the process that serves MQ messages to the windows client over a web
service.

#### srreporter
This is the process that reports test results from the clients to datazilla.m.o,
and emails successful test results from "pushed" runs to the user.

#### sremailer
This exposes a web service for machines that are not the master to send emails
outside the testbed (used by clients to send failed test notifications).

#### cron jobs
There are two cron jobs running on the master. One that runs every night at 5am
Pacific, to kick off a full run of tests on the latest nightly build, and one
that runs every minute to check the "push" server (currently hosted on heroku)
to see if anyone has asked to run tests against a try build.

## Server
stone-ridge-linux1.dmz.scl3.mozilla.com (broadband)
stone-ridge-linux2.dmz.scl3.mozilla.com (umts)
stone-ridge-linux3.dmz.scl3.mozilla.com (gsm)

These machines are responsible for shaping network traffic to and from them to
make it behave like the netconfig they are assigned to. Additionally, they serve
test content to the clients via HTTP, as well as acting as DNS servers for
the clients that are configured to be talking to them (so we can use real
hostnames but have their traffic directed over a properly simulated network).
They also record traffic during a test run to be used for debugging purposes in
case something goes wrong, or we wonder why a particular test behaves the way it
does.

### Processes running on the servers

#### apache
This is a special build of apache, with some modifications to mod\_rewrite that
allows for serving files with their original headers (as recorded from the
public internet) and allowing different versions of a URL based on the query
string. This is what serves test content to the clients.

#### srscheduler
This receives test requests from the master and farms them out to the clients as
appropriate. This is mostly an artifact from the time when I was intending to
only have one client sending traffic to a server at a time (to reduce
interference between clients). That plan was thrown out the window by windows
being flaky with RabbitMQ. Instead of removing this process entirely, I just
made it dumber to avoid having to rearchitect things even further. Fortunately,
interaction between multiple clients and one server seems to have little
(if any) effect on the test results.

#### srnamed
This serves DNS responses to the clients. For the most part, it only replies
the server's own IP address, but for a few limited hostnames (each machine in
the stone ridge testbed, as well as puppet) it responds with the actual IPs of
those machines.

#### srpcapper
This runs tcpdump for every test that is run against the server, and serves the
final pcap to the clients for archival. The reason we run this on the server
instead of on the clients is that I was unable to make OS X or Win7 reliably
give a full pcap of the traffic.

#### interface startup
A script that runs on system startup to configure network traffic shaping on the
interface that is connected to the stone ridge switch.

## Client
stone-ridge-linux4.dmz.scl3.mozilla.com (CentOS 6)
stone-ridge-mac1.dmz.scl3.mozilla.com (Mac OS X 10.8)
stone-ridge-win1.dmz.scl3.mozilla.com (Windows 7)

These machines run the tests against each of the selected netconfig servers in
turn, record the results, and report them to the master. Each of these machines
has its monitor port plugged into an Extron EDID and has a user automatically
logged in on the graphical terminal. This user has a terminal in its startup
items, and it is this terminal that runs the worker process. We do this because,
like TpWhateverWeCallItNow, we need a way to display an actual firefox for some
of the stone ridge tests.

### Processes running on the clients

#### srworker
This is the process that takes requests from the scheduler on the server and
runs tests based on those requests. It runs as a regular user in a terminal
in an automatically logged-in GUI session.

#### srdns
This daemon runs as root to allow the test processes to change the DNS servers
of the local machine based on which netconfig is currently being tested against.
This is a service on Win7 (written in C#), and a python daemon on Linux and
OS X. This python daemon has untested code to replace the C# service on Win7.

#### srcleaner
This process runs periodically to clean up any excess disk space used by data
from old test runs.

# Test overview

* Master receives a request to run some subset of the tests
* Master downloads the builds for this run from ftp.m.o
* Master tells servers that they need to schedule tests
* Server tells clients to run tests against it
* Client runs all its tests
* Client packages up results
* Client sends results to server
* Server reports results to datazilla
* If necessary, emails are sent to the requesting user with results

## Client details

Since most of the really interesting code is run on the client, we'll get
into the details of that here. When the client's srworker process receives
a request to run a test, here's what it does.

First, it creates a working directory for this test run that is named for the
srid (Stone Ridge IDentifier) that has been generated on the master. The srid is
either a combination of LDAP email and HG SHA (for try runs), or a
randomly-generated UUID (for nightly runs). In this directory, all the logs from
the run will be stored, as well as configuration for the run, the build used for
the run, and the results of the tests.

Once the configuration is written, and any necessary subdirectories are made,
the following processes are run.

### srdownloader
This process downloads the firefox build and test zip from the master.

### srunpacker
This process extracts the firefox binary from the packaged build, and extracts
the appropriate files (e.g. xpcshell) from the test zip, and places them in
a well-known location in the working directory for the run.

### srinfogatherer
This process extracts metadata about the current build and client and stores it
in json format that is later used to generate results that can be uploaded to
datazilla.

### srpcap (with the argument --start)
This process calls out to a web service on the appropriate server to have it
start running tcpdump for this test run.

### srdnsupdater
This process talks to the srdns daemon (see above) and has it change the
client's DNS servers to point at the server for the netconfig being tested
against.

### srdnscheck
This is a sanity check process to make sure our DNS servers have been properly
changed. If the sanity check fails, the test is aborted.

### srarpfixer
This sends a single ping to the server to make sure we have a properly updated
ARP cache for its IP, so the numbers of the basic test all make sense across
all client platforms.

### srrunner
This is the process that actually runs the tests. It looks in a well-known
location for test files. These files are named either <testsuite>.js or
<testsuite>.page. Documentation on the format of these files is below.
Each of these tests are run, with their output being saved to the working
directory for this run as <testsuite>.<originalextension>.out. Additionally,
any stdout or stderr data from the process that ran the test file is saved
to <testsuite>.<originalextension>.process.out.

### srdnsupdater (with the argument --restore)
This instance of srdnsupdater talks to the srdns daemon and has it restore the
client's DNS servers to the official ones handed out by DHCP.

### srdnscheck (with the argument --public)
This sanity checks the last run of srdnsupdater to make sure we have DNS
responses that correspond to the public internet instead of the private
stone ridge testbed.

### srpcap (with the argument --stop)
This has the server stop the tcpdump process associated with this run, downloads
the resulting pcap file, and saves it with the rest of the output.

### srcollator
This process goes through each of the <testsuite>.<originalextension>.out files
and comibnes them with the information extracted by srinfogatherer to make files
that can be uploaded to datazilla.

### srarchiver
This process zips up all the output from this test run to be saved for later.

### sruploader
This process uploads all the results from this test run to the master via
RabbitMQ, where it is then reported to datazilla.

## Test types
There are two kinds of tests that can be run by stone ridge. They are
differentiated based on their filename. Test files ending in .js are run
under xpcshell, with a framework similar to (but not exactly the same as!)
xpcshell-based unit tests. Test files ending in .page are run in a full
firefox process, with a framework similar to (but not exactly the same as!)
the talos pageloader tests. The xpcshell tests have all the functions in
head.js and srdata.js available to them. The full firefox tests are run
by a pageloader extension that lives under pageloader/ combined with srdata.js
The file srdata.js is what is used to record and save test result data, which is
why it is shared between both xpcshell and pageloader test types.

# Other important files

## srrun.py
This is a wrapper program used to set up the appropriate environment to run a
stone ridge python program from the command line, setting things such as
PYTHONPATH and using the appropriate python interpreter. Similar to virtualenv,
but for some reason (I can't remember what, now), I opted against using
virtualenv.

## stoneridge.py
This is the stoneridge library that holds code used by more than one of the
stone ridge programs lsited above.

## tools/
A directory containing extra tools useful for stone ridge

### srenqueuer.py
This is the program that is run periodically on the master to check for pushed
try builds to run under stone ridge.

### srpush.py
This is the command-line program used by end-users to push a try build to stone
ridge for testing.

### wprexplode.py
This is used to create apache configurations and files to be served from a
web-page-replay archive.

## wpr/
Google's web-page-replay. Used by srnamed for DNS functionality, and to record
page loads to be turned into .page-style tests.

### dnsproxy.py
This is used by srdns to provide DNS server capabilities.

### replay.py
This can be used by a developer to record a pageload to be transformed into a
.page-style test.

### httparchive.py
This is used by wprexplode.py (see above) to parse the output of replay.py.

# Pushing to Stone Ridge
Right now, a very limited set of people have access to push to stone ridge (that
set of people being the necko team). To do so, you first have to make a build on
try with opt builds (windows fails to run the stone ridge tests with debug
builds). You can make builds for macosx64, win32, and linux64. The other
platforms are not supported. Once you have that build, and the sha associated
with it, you can use srpush.py (see above) to send a command to the stone ridge
push infrastructure. Right now, this is hosted on heroku (a cheap and dirty
hack to avoid standing up even more infrastructure in Mozilla's network). The
information in heroku is read periodically by srenqueuer.py on the master and
run from there as a normal stone ridge run. Results are emailed to the user
that requested the run. The code for the server that runs on heroku is at
https://github.com/todesschaf/srpush
