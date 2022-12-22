import cmd
from shlex import shlex
from progress.bar import Bar
from getpass import getpass
import argparse
import shlex
import re
from prettytable import PrettyTable
import json
import requests

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

nsx_address = '172.30.77.57'

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

class NSX(cmd.Cmd):
    prompt = f'{color.BOLD}{color.GREEN}nsx-t >{color.END} '

    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.auth()
        self.do_sync()
    
    def auth(self):
        user = input("login: ")
        user += "@ouiit.local"
        password = getpass()
        self.session.auth = (user, password)

    def do_sync(self):
        self.segments = []
        raw_segments = self.session.get(f'https://{nsx_address}/policy/api/v1/infra/segments', verify=False)
        segments = json.loads(raw_segments.content).get("results")
        bar = Bar('Syncing segments', max=len(segments))
        for segment in segments:
            if "vlan_ids" in segment.keys():
                bar.next()
                continue
            logical_ports = self.session.get(f'https://{nsx_address}/policy/api/v1/infra/segments/{segment["id"]}/ports/', verify=False)
            ports = json.loads(logical_ports.content).get("results")
            ports = ports if ports else []
            segment["logical_ports"] = ports
            self.segments.append(segment)
            bar.next()
        bar.finish()

    def do_ls(self, line):
        """
        List and filter segments
        Use 'ls --help' to get some help
        """
        agparser = argparse.ArgumentParser(prog='ls')
        agparser.add_argument("--detach", action='store_true', help='List detached segments')
        agparser.add_argument("--filter", required=False, help='Filter output by display_name. Excpects regex')
        agparser.add_argument("--subnet", required=False, help='Filter output by subnet. Excpects regex')
        agparser.add_argument("--user", required=False, help='Filter output by user. Excpects regex')
        try:
            args = agparser.parse_args(shlex.split(line))
        except SystemExit:
            return False
        
        t = PrettyTable(['Name', 'ID', 'Ports', 'Subnets', 'CreatedBy'])
        for segment in self.segments:
            decision = True
            nets = ""
            if segment.get("subnets"):
                nets = ",".join([ net["network"] for net in segment["subnets"] ])
            if args:
                if args.filter and not re.search(args.filter, segment["display_name"]):
                    decision = False
                if args.subnet and not re.search(args.subnet, nets):
                    decision = False
                if args.user and not re.search(args.user, segment["_create_user"]):
                    decision = False
                if args.detach and len(segment["logical_ports"]) != 0:
                    decision = False
            if decision:
                t.add_row( [ segment["display_name"], segment["id"], len(segment["logical_ports"]), nets, segment["_create_user"] ] )
        print(t)
    
    def do_rm(self, id):
        """
            Remove a segment by ID
        """
        logical_ports = self.session.get(f'https://{nsx_address}/policy/api/v1/infra/segments/{id}/ports/', verify=False)
        ports = json.loads(logical_ports.content).get("results")
        if len(ports) > 0 :
            for port in ports:
                print(f"Detach port {port['display_name']}")
                self.session.post(f'https://{nsx_address}/policy/api/v1/infra/realized-state/realized-entity?action=refresh&intent_path=/infra/segments/{id}/ports/{port["unique_id"]}', verify=False)
                self.session.get(f'https://{nsx_address}/policy/api/v1/search?query=resource_type:SegmentPort AND path:"/infra/segments/{id}/ports/{port["unique_id"]}"', verify=False)
                self.session.delete(f'https://{nsx_address}/api/v1/logical-ports/{port["unique_id"]}?detach=true', verify=False)
        
        print( f'Removing {id}...' )
        self.session.delete(f'https://{nsx_address}/policy/api/v1/infra/segments/{id}/segment-discovery-profile-binding-maps/default', verify=False)
        self.session.delete(f'https://{nsx_address}/policy/api/v1/infra/segments/{id}/segment-security-profile-binding-maps/default', verify=False)
        seg = self.session.delete(f'https://{nsx_address}/policy/api/v1/infra/segments/{id}', verify=False)
        
        if seg.status_code == 200:
            print(f'{id} is deleted')
        else:
            print(f'Failed to delete {id}!')
    
    def do_describe(self, id):
        """
        Show info about a segment and its connected ports
        """
        raw_segment = self.session.get(f'https://{nsx_address}/policy/api/v1/infra/segments/{id}', verify=False)
        segment = json.loads(raw_segment.content)
        if raw_segment.status_code != 200:
            print("The segment was not found")
            return False

        # Print INFO about the segment
        print(f'{color.BOLD}Display name:{color.END} {segment["display_name"]}')
        print(f'{color.BOLD}ID:{color.END} {id}')
        print(f'{color.BOLD}Cretaed by:{color.END} {segment["_create_user"]}')

        # Print INFO about the ports
        logical_ports = self.session.get(f'https://{nsx_address}/policy/api/v1/infra/segments/{id}/ports/', verify=False)
        ports = json.loads(logical_ports.content).get("results")
        t = PrettyTable(['ID', 'NAME', 'Status'])
        if len(ports) > 0 :
            for port in ports:
                # Refresh info about the port and get it's status
                # The port can be attached to VM which does not exists
                self.session.post(f'https://{nsx_address}/policy/api/v1/infra/realized-state/realized-entity?action=refresh&intent_path=/infra/segments/{id}/ports/{port["id"]}', verify=False)
                port_state_raw = self.session.get(f'https://{nsx_address}/policy/api/v1/search?query=resource_type:SegmentPort AND path:"/infra/segments/{id}/ports/{port["id"]}"', verify=False)
                port_state = json.loads(port_state_raw.content).get("results")
                status = port_state[0]["status"]["consolidated_status"]["consolidated_status"]
                t.add_row( [ port["unique_id"], port["display_name"], status ] )
        print(t)

    def do_EOF(self, line):
        return True

if __name__ == '__main__':
    NSX().cmdloop()