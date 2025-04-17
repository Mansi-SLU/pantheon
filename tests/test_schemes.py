#!/usr/bin/env python

import os
from os import path
import sys
import time
import signal
import argparse

import context
from helpers import utils
from helpers.subprocess_wrappers import Popen, check_output, call


def test_schemes(args):
    wrappers_dir = path.join(context.src_dir, 'wrappers')

    if args.all:
        schemes = utils.parse_config()['schemes'].keys()
    elif args.schemes is not None:
        schemes = args.schemes.split()

    for scheme in schemes:
        sys.stderr.write('Testing %s...\n' % scheme)
        src = path.join(wrappers_dir, scheme + '.py')

        run_first = check_output([src, 'run_first']).strip()
        run_second = 'receiver' if run_first == 'sender' else 'sender'

        port = utils.get_open_port()

        # run first to run
        cmd = [src, run_first, port]
        first_proc = Popen(cmd, preexec_fn=os.setsid)

        # wait for 'run_first' to be ready
        time.sleep(3)

        # run second to run
        cmd = [src, run_second, '127.0.0.1', port]
        second_proc = Popen(cmd, preexec_fn=os.setsid)

        # === Start ping for RTT/loss logging ===
        ping_output_file = f'/tmp/{scheme}_ping.txt'
        ping_proc = Popen(['ping', '-i', '0.2', '-c', '300', '127.0.0.1'],
                          stdout=open(ping_output_file, 'w'), stderr=open(os.devnull, 'w'))

        # === Capture iperf-like output for throughput ===
        iperf_log_file = f'/tmp/{scheme}_iperf.txt'
        env = os.environ.copy()
        env["IPERF_LOG_FILE"] = iperf_log_file  # your wrapper should respect this if needed

        # test lasts for 60 seconds
        signal.signal(signal.SIGALRM, utils.timeout_handler)
        signal.alarm(60)

        try:
            for proc in [first_proc, second_proc]:
                proc.wait()
                if proc.returncode != 0:
                    sys.exit('%s failed in tests' % scheme)
        except utils.TimeoutError:
            pass
        except Exception as exception:
            sys.exit('test_schemes.py: %s\n' % exception)
        else:
            signal.alarm(0)
            sys.exit('test exited before time limit')
        finally:
            # cleanup
            utils.kill_proc_group(first_proc)
            utils.kill_proc_group(second_proc)

            if ping_proc.poll() is None:
                ping_proc.terminate()
                ping_proc.wait()

            # === Process metrics ===
            avg_rtt = -1
            loss_rate = -1
            throughput = -1

            if os.path.exists(ping_output_file):
                with open(ping_output_file, 'r') as f:
                    ping_data = f.read()

                    import re
                    rtt_match = re.search(r'rtt min/avg/max/mdev = [\d\.]+/([\d\.]+)', ping_data)
                    avg_rtt = float(rtt_match.group(1)) if rtt_match else -1

                    loss_match = re.search(r'(\d+)% packet loss', ping_data)
                    loss_rate = float(loss_match.group(1)) / 100 if loss_match else 0.0

            if os.path.exists(iperf_log_file):
                with open(iperf_log_file, 'r') as f:
                    for line in f:
                        if 'bits/sec' in line:
                            match = re.search(r'([\d\.]+)\s+([KMG])bits/sec', line)
                            if match:
                                val, unit = float(match.group(1)), match.group(2)
                                unit_map = {'K': 1e3, 'M': 1e6, 'G': 1e9}
                                throughput = val * unit_map.get(unit, 1)
                                break

            # === Log metrics ===
            log_path = f'results/test_metrics_{scheme}.log'
            os.makedirs('results', exist_ok=True)
            with open(log_path, 'w') as logf:
                logf.write(f"Scheme: {scheme}\n")
                logf.write(f"RTT (ms): {avg_rtt:.2f}\n")
                logf.write(f"Loss Rate: {loss_rate:.4f}\n")
                logf.write(f"Throughput (bps): {throughput:.2f}\n")

            print(f"[METRICS] Scheme: {scheme}")
            print(f"[METRICS] RTT: {avg_rtt:.2f} ms")
            print(f"[METRICS] Loss Rate: {loss_rate:.4f}")
            print(f"[METRICS] Throughput: {throughput:.2f} bps")


def cleanup():
    cleanup_src = path.join(context.base_dir, 'tools', 'pkill.py')
    cmd = [cleanup_src, '--kill-dir', context.base_dir]
    call(cmd)


def main():
    parser = argparse.ArgumentParser()

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true',
                       help='test all the schemes specified in src/config.yml')
    group.add_argument('--schemes', metavar='"SCHEME1 SCHEME2..."',
                       help='test a space-separated list of schemes')

    args = parser.parse_args()

    try:
        test_schemes(args)
    except:
        cleanup()
        raise
    else:
        sys.stderr.write('Passed all tests!\n')


if __name__ == '__main__':
    main()
