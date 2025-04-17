#!/usr/bin/env python

import signal
import argparse
from helpers.subprocess_wrappers import call

# prevent this script from being killed before cleaning up using pkill
def signal_handler(signum, frame):
    pass

def main():
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--kill-dir', metavar='DIR', help='kill all scripts in the directory')
    args = parser.parse_args()

    # kill known Mahimahi and iperf processes
    pkill_cmds = [
        'pkill -f mm-delay',
        'pkill -f mm-link',
        'pkill -f mm-loss',
        'pkill -f mm-tunnelclient',
        'pkill -f mm-tunnelserver',
        'pkill -f -SIGKILL iperf'
    ]

    # Optional: only kill specific Pantheon subprocesses from the directory, not everything
    if args.kill_dir:
        # Cautiously kill only scripts known to be part of Pantheon
        pantheon_targets = ['run_first', 'run_second', 'run_sender', 'run_receiver']
        for target in pantheon_targets:
            pkill_cmds.append(f"pkill -f {args.kill_dir}/src/wrappers/{target}")

    for cmd in pkill_cmds:
        call(cmd, shell=True)

if __name__ == '__main__':
    main()
