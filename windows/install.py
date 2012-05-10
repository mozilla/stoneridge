import os
import subprocess

mydir = os.path.split(os.path.abspath(__file__))[0]

# Install the dns modifier service
windnssvc = os.path.join(mydir, 'srdns.exe')
subprocess.call(['sc.exe', 'create', 'srdns', 'binPath=', windnssvc,
                 'DisplayName=', 'Stone Ridge DNS Modifier', 'start=', 'auto'])

# Start the dns modifier service
subprocess.call(['sc.exe', 'start', 'srdns'])
