using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Diagnostics;
using System.ServiceProcess;
using System.Threading;
using System.Net.Sockets;
using System.Net;
using Microsoft.Win32;

namespace neckodnssvc
{
    class NeckoDnsSvc : System.ServiceProcess.ServiceBase
    {
        protected TimeSpan stopdelay;
        protected ManualResetEvent shutdownevt;
        protected Thread thread;
        protected string logsrc;
        protected string logname;

        public NeckoDnsSvc()
        {
            stopdelay = new TimeSpan(0, 0, 0, 1);

            logsrc = "StoneRidgeDNS";
            logname = "Application";
            if (!EventLog.SourceExists(logsrc))
            {
                EventLog.CreateEventSource(logsrc, logname);
            }
        }

        public void setDns(string dns)
        {
            /* First, kill the WAN interface */
            EventLog.WriteEntry(logsrc, "About to kill WAN interface");
            Process wanproc = new Process();
            wanproc.StartInfo.FileName = "netsh.exe";
            wanproc.StartInfo.Arguments = "interface set interface name=WAN admin=DISABLED";
            wanproc.StartInfo.UseShellExecute = false;
            wanproc.StartInfo.RedirectStandardOutput = true;
            wanproc.Start();
            wanproc.WaitForExit();
            EventLog.WriteEntry(logsrc, "netsh exited with code " + wanproc.ExitCode.ToString());

            /* Next, clear the domain search suffix */
            EventLog.WriteEntry(logsrc, "About to clear search suffix");
            Registry.SetValue("HKEY_LOCAL_MACHINE\\System\\CurrentControlSet\\Services\\TCPIP\\Parameters", "SearchList", "");
            EventLog.WriteEntry(logsrc, "Cleared search suffix");

            /* Finally, set our static DNS server on the StoneRidge interface */
            EventLog.WriteEntry(logsrc, "About to set DNS on StoneRidge interface");
            Process srproc = new Process();
            srproc.StartInfo.FileName = "netsh.exe";
            srproc.StartInfo.Arguments = "interface ipv4 set dnsservers StoneRidge static " + dns + " validate=no";
            srproc.StartInfo.UseShellExecute = false;
            srproc.StartInfo.RedirectStandardOutput = true;
            srproc.Start();
            srproc.WaitForExit();
            EventLog.WriteEntry(logsrc, "netsh exited with code " + srproc.ExitCode.ToString());
        }

        public void resetDns()
        {
            /* First, kill the DNS server on the StoneRidge interface */
            EventLog.WriteEntry(logsrc, "About to kill DNS on StoneRidge interface");
            Process srproc = new Process();
            srproc.StartInfo.FileName = "netsh.exe";
            srproc.StartInfo.Arguments = "interface ipv4 set dnsservers StoneRidge static none validate=no";
            srproc.StartInfo.UseShellExecute = false;
            srproc.StartInfo.RedirectStandardOutput = true;
            srproc.Start();
            srproc.WaitForExit();
            EventLog.WriteEntry(logsrc, "netsh exited with code " + srproc.ExitCode.ToString());

            /* Next, bring the WAN interface back up*/
            EventLog.WriteEntry(logsrc, "About to resurrect WAN interface");
            Process wanproc = new Process();
            wanproc.StartInfo.FileName = "netsh.exe";
            wanproc.StartInfo.Arguments = "interface set interface name=WAN admin=ENABLED";
            wanproc.StartInfo.UseShellExecute = false;
            wanproc.StartInfo.RedirectStandardOutput = true;
            wanproc.Start();
            wanproc.WaitForExit();
            EventLog.WriteEntry(logsrc, "netsh exited with code " + wanproc.ExitCode.ToString());

            /* Finally, re-set the domain search suffix */
            EventLog.WriteEntry(logsrc, "About to re-set search suffix");
            Registry.SetValue("HKEY_LOCAL_MACHINE\\System\\CurrentControlSet\\Services\\TCPIP\\Parameters", "SearchList", "mozilla.com");
            EventLog.WriteEntry(logsrc, "Re-set search suffix");
        }

        public void svcMain()
        {
            // Set up our master socket
            Socket s = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
            IPEndPoint e = new IPEndPoint(IPAddress.Loopback, 63250);
            s.Bind(e);
            s.Listen(0);

            // Main "event" loop
            while (true)
            {
                // See if we're supposed to shut down
                if (shutdownevt.WaitOne(stopdelay, true))
                    break;

                // Wait 1 second (in us) for a connection
                if (!s.Poll(10000, SelectMode.SelectRead))
                    continue;

                Socket sock = s.Accept();

                // Got a connection, figure out what to do (first 2 bytes define the operation)
                byte[] msghdr = new byte[2];
                sock.Receive(msghdr, 2, SocketFlags.None);

                string shdr = Encoding.ASCII.GetString(msghdr);
                if (shdr[0].Equals('s'))
                {
                    // We got a set command. It contains the length of the dotted quad (in
                    // bytes). Read the ip from the socket and set it
                    byte[] ip = new byte[msghdr[1]];
                    sock.Receive(ip, msghdr[1], SocketFlags.None);
                    string ipstr = Encoding.ASCII.GetString(ip);
                    this.setDns(ipstr);
                }
                else if (shdr[0].Equals('r'))
                {
                    // We got a reset command
                    this.resetDns();
                }
                else
                {
                    string data = Encoding.ASCII.GetString(msghdr);
                    Console.WriteLine("Got message: " + data);
                }

                // Send our response
                byte[] resp = new byte[2];
                resp[0] = (byte)'o';
                resp[1] = (byte)'k';
                sock.Send(resp);
                sock.Close();
            }

            // Clean up!
            s.Close();
        }

        protected override void OnStart(string[] args)
        {
            ThreadStart ts = new ThreadStart(this.svcMain);
            shutdownevt = new ManualResetEvent(false);
            thread = new Thread(ts);
            thread.Start();
        }

        protected override void OnStop()
        {
            shutdownevt.Set();
            thread.Join(60000); // wait up to 1 min for thread to stop
        }

        static void Main(string[] args)
        {
            ServiceBase[] svcs = new ServiceBase[] { new NeckoDnsSvc() };
            ServiceBase.Run(svcs);
        }
    }
}
