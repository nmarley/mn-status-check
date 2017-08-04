#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import socket
import argparse
import simplejson as json
from bitcoinrpc.authproxy import JSONRPCException
libpath = os.path.normpath(os.path.join(os.path.dirname(__file__), '../lib'))
sys.path.append(libpath)


def is_dashd_port_open(dashd):
    # test socket open before beginning, display instructive message to MN
    # operators if it's not
    port_open = False
    try:
        info = dashd.rpc_command('getgovernanceinfo')
        port_open = True
    except (socket.error, JSONRPCException) as e:
        print("%s" % e)

    return port_open


def build_cloudwatch_cmd(status):
    cmd = """
aws cloudwatch put-metric-data \\
  --namespace DashCore \\
  --metric-name MasternodeStatus \\
  --dimensions Hostname={},Network={} \\
  --value {}
    """.format(socket.gethostname(),
               status['network'],
               status['status_ok'])

    return cmd


def main():
    from dashd import DashDaemon
    options = process_args()

    dashd = DashDaemon.from_dash_conf(options.dash_config)

    # check dashd connectivity
    if not is_dashd_port_open(dashd):
        print("Cannot connect to dashd. Please ensure dashd is running "
              "and the JSONRPC port open.")
        return

    mn_status = dashd.mn_status()
    print(json.dumps(mn_status))

    if options.cloudwatch:
        cmd = build_cloudwatch_cmd(mn_status)
        print("cmd = ...")
        print(cmd)
        print("Sending metric to CloudWatch...", end='')
        sys.stdout.flush()

        os.environ['PATH'] = "/usr/local/bin:%s" % os.environ.get('PATH')

        os.system(cmd)
        print(" done.")


def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--dash-conf',
                        required=True,
                        help='dash config file with credentials',
                        dest='dash_config')
    parser.add_argument('--send-cloudwatch-metric',
                        required=False,
                        help='send masternode status metric (0 or 1) to \
                              AWS CloudWatch via awscli',
                        action='store_true',
                        dest='cloudwatch')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    main()
