"""
dashd JSONRPC interface
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
import base58
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from masternode import Masternode
from decimal import Decimal
import time
import re


class DashDaemon():
    def __init__(self, **kwargs):
        host = kwargs.get('host', '127.0.0.1')
        user = kwargs.get('user')
        password = kwargs.get('password')
        port = kwargs.get('port')

        self.creds = (user, password, host, port)

        # memoize calls to some dashd methods
        self.governance_info = None
        self.gobject_votes = {}

    @property
    def rpc_connection(self):
        return AuthServiceProxy("http://{0}:{1}@{2}:{3}".format(*self.creds))

    @classmethod
    def from_dash_conf(self, dash_dot_conf):
        from dash_config import DashConfig
        config_text = DashConfig.slurp_config_file(dash_dot_conf)
        creds = DashConfig.get_rpc_creds(config_text, os.environ.get('DASH_NETWORK', 'mainnet'))

        return self(**creds)

    def rpc_command(self, *params):
        return self.rpc_connection.__getattr__(params[0])(*params[1:])

    # common RPC convenience methods
    def is_testnet(self):
        return self.rpc_command('getinfo')['testnet']

    def get_masternodes(self):
        mnlist = self.rpc_command('masternodelist', 'full')
        return [Masternode(k, v) for (k, v) in mnlist.items()]

    def get_object_list(self):
        try:
            golist = self.rpc_command('gobject', 'list')
        except JSONRPCException as e:
            golist = self.rpc_command('mnbudget', 'show')
        return golist

    def get_current_masternode_vin(self):
        my_vin = None

        try:
            status = self.rpc_command('masternode', 'status')
            my_vin = self.parse_masternode_status_vin(status['vin'])
        except JSONRPCException as e:
            pass

        return my_vin

    def governance_quorum(self):
        # TODO: expensive call, so memoize this
        total_masternodes = self.rpc_command('masternode', 'count', 'enabled')
        min_quorum = self.govinfo['governanceminquorum']

        # the minimum quorum is calculated based on the number of masternodes
        quorum = max(min_quorum, (total_masternodes // 10))
        return quorum

    @property
    def govinfo(self):
        if (not self.governance_info):
            self.governance_info = self.rpc_command('getgovernanceinfo')
        return self.governance_info

    # governance info convenience methods
    def superblockcycle(self):
        return self.govinfo['superblockcycle']

    def governanceminquorum(self):
        return self.govinfo['governanceminquorum']

    def proposalfee(self):
        return self.govinfo['proposalfee']

    def last_superblock_height(self):
        height = self.rpc_command('getblockcount')
        cycle = self.superblockcycle()
        return cycle * (height // cycle)

    def next_superblock_height(self):
        return self.last_superblock_height() + self.superblockcycle()

    def is_masternode(self):
        return not (self.get_current_masternode_vin() is None)

    def mn_status(self):
        status = {}

        try:
            rpc_mn_status = self.rpc_command('masternode', 'status')
            vin = self.parse_masternode_status_vin(rpc_mn_status['vin'])

            mnlist = self.rpc_command('masternodelist', 'full', vin)

            mn_queue_status = ''
            if mnlist:
                val = mnlist.get(vin)
                mn = Masternode(vin, val)
                mn_queue_status = mn.status

            status_ok = 0.0
            if rpc_mn_status['status'] == 'Masternode successfully started' \
               and mn_queue_status == 'ENABLED':
                status_ok = 1.0

            status = {
                'status_message': rpc_mn_status['status'],
                'vin': vin,
                'queue_status': mn_queue_status,
                'network': 'testnet' if self.is_testnet() else 'mainnet',
                'status_ok': status_ok,
            }

        except JSONRPCException as e:
            pass

        return status

    def is_synced(self):
        mnsync_status = self.rpc_command('mnsync', 'status')
        synced = (mnsync_status['IsBlockchainSynced'] and
                  mnsync_status['IsMasternodeListSynced'] and
                  mnsync_status['IsWinnersListSynced'] and
                  mnsync_status['IsSynced'] and
                  not mnsync_status['IsFailed'])
        return synced

    def current_block_hash(self):
        height = self.rpc_command('getblockcount')
        block_hash = self.rpc_command('getblockhash', height)
        return block_hash

    def parse_masternode_status_vin(self, status_vin_string):
        status_vin_string_regex = re.compile('CTxIn\(COutPoint\(([0-9a-zA-Z]+),\\s*(\d+)\),')

        m = status_vin_string_regex.match(status_vin_string)
        txid = m.group(1)
        index = m.group(2)

        vin = txid + '-' + index
        if (txid == '0000000000000000000000000000000000000000000000000000000000000000'):
            vin = None

        return vin
