#!/usr/bin/env python

import subprocess

ip_mappings = {
    '172.17.0.1': '2C-76-8A-D0-CE-89',  # Broadband
    '172.18.0.1': '2C-76-8A-D0-CA-D9',  # UMTS
    '172.19.0.1': '2C-76-8A-D0-CE-B9',  # GSM
}

for ip, mac in ip_mappings.items():
    p = subprocess.Popen(['arp', '-s', ip, mac, '172.16.1.2'],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.wait()
