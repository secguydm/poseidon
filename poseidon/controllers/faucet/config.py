
import os
from faucetconfrpc.faucetconfrpc_client_lib import FaucetConfRpcClient
from poseidon.controllers.faucet.helpers import get_config_file, yaml_in, yaml_out


class FaucetConfGetSetter:

    DEFAULT_CONFIG_FILE = ''

    def __init__(self, **_kwargs):
        self.faucet_conf = {}

    @staticmethod
    def config_file_path(config_file):
        return config_file

    def set_acls(self, acls):
        self.faucet_conf['acls'] = acls

    def get_dps(self):
        return self.faucet_conf['dps']

    def get_switch_conf(self, dp):
        return self.get_dps().get(dp, None)

    def get_port_conf(self, dp, port):
        switch_conf = self.get_switch_conf(dp)
        if not switch_conf:
            return None
        return switch_conf['interfaces'].get(port, None)

    def set_port_conf(self, dp, port, port_conf):
        switch_conf = self.get_switch_conf(dp)
        if not switch_conf:
            return None
        switch_conf['interfaces'][port] = port_conf

    def set_switch_conf(self, dp, switch_conf):
        self.faucet_conf['dps'][dp] = switch_conf

    def get_stack_root_switch(self):
        root_stack_switch = [
            switch for switch, switch_conf in self.get_dps().items()
            if switch_conf.get('stack', {}).get('priority', None)]
        if root_stack_switch:
            return root_stack_switch[0]
        return None

    def set_mirror_config(self, dp, port, ports):
        mirror_interface_conf = self.get_port_conf(dp, port)
        if not mirror_interface_conf:
            return
        if ports:
            if isinstance(ports, set):
                ports = list(ports)
            if not isinstance(ports, list):
                ports = [ports]
            mirror_interface_conf['mirror'] = ports
        # Don't delete DP level config when setting mirror list to empty,
        # as that could cause an unnecessary cold start.
        elif 'mirror' in mirror_interface_conf:
            del mirror_interface_conf['mirror']
        self.set_port_conf(dp, port, mirror_interface_conf)


class FaucetLocalConfGetSetter(FaucetConfGetSetter):

    def read_faucet_conf(self, config_file):
        if not config_file:
            config_file = self.DEFAULT_CONFIG_FILE
        assert config_file
        config_file = get_config_file(config_file)
        faucet_conf = yaml_in(config_file)
        if isinstance(faucet_conf, dict):
            self.faucet_conf = faucet_conf
        return self.faucet_conf

    def write_faucet_conf(self, config_file=None, faucet_conf=None):
        if not config_file:
            config_file = self.DEFAULT_CONFIG_FILE
        if faucet_conf is None:
            faucet_conf = self.faucet_conf
        assert set(faucet_conf.keys()).issubset(
            set(['dps', 'acls', 'vlans', 'include'])), set(faucet_conf.keys())
        self.faucet_conf = faucet_conf
        config_file = get_config_file(config_file)
        return yaml_out(config_file, self.faucet_conf)


class FaucetRemoteConfGetSetter(FaucetConfGetSetter):

    def __init__(self, client_key=None, client_cert=None,
                 ca_cert=None, server_addr=None):
        self.client = FaucetConfRpcClient(
            client_key=client_key, client_cert=client_cert,
            ca_cert=ca_cert, server_addr=server_addr)

    @staticmethod
    def config_file_path(config_file):
        if config_file:
            return os.path.basename(config_file)
        return config_file

    def read_faucet_conf(self, config_file):
        self.faucet_conf = self.client.get_config_file(
            config_filename=self.config_file_path(config_file))
        return self.faucet_conf

    def write_faucet_conf(self, config_file=None, faucet_conf=None):
        if not config_file:
            config_file = self.DEFAULT_CONFIG_FILE
        if faucet_conf is None:
            faucet_conf = self.faucet_conf
        assert set(faucet_conf.keys()).issubset(
            set(['dps', 'acls', 'vlans', 'include'])), set(faucet_conf.keys())
        self.faucet_conf = faucet_conf
        return self.client.set_config_file(
            self.faucet_conf,
            config_filename=self.config_file_path(config_file),
            merge=False)

