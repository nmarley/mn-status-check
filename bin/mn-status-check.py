#!/usr/bin/env python
import sys
import os
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), '../lib')))
from dashd import DashDaemon
import socket
import time
from bitcoinrpc.authproxy import JSONRPCException
import signal
import argparse
import simplejson as json


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
    options = process_args()

    dashd = DashDaemon.from_dash_conf(config.dash_conf)

    # check dashd connectivity
    if not is_dashd_port_open(dashd):
        print("Cannot connect to dashd. Please ensure dashd is running and the JSONRPC port open.")
        return

    # check dashd sync
    if not dashd.is_synced():
        print("dashd not synced with network! Awaiting full sync before running.")
        return

    if options.status_check:
        printdbg("--masternode-status option used, reporting status only")
        mn_status = dashd.mn_status()
        print(json.dumps(mn_status))
        return

    # ensure valid masternode
    if not dashd.is_masternode():
        print("Invalid Masternode Status, cannot continue.")
        return


def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--dash-conf',
                        required=True,
                        help='dash config file with credentials',
                        dest='dash_config')
    parser.add_argument('-s', '--masternode-status',
                        action='store_true',
                        help='Masternode status check and exit',
                        dest='status_check')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    main()
