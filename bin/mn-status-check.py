#!/usr/bin/env python
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


def main():
    from dashd import DashDaemon
    options = process_args()

    dashd = DashDaemon.from_dash_conf(options.dash_config)

    # check dashd connectivity
    if not is_dashd_port_open(dashd):
        print("Cannot connect to dashd. Please ensure dashd is running \
               and the JSONRPC port open.")
        return

    mn_status = dashd.mn_status()
    print(json.dumps(mn_status))


def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--dash-conf',
                        required=True,
                        help='dash config file with credentials',
                        dest='dash_config')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    main()
