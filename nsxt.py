import cmd
import json
import shlex
from getpass import getpass
import argparse
import re
from prettytable import PrettyTable
import requests
import jq

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

NSX_ADDRESS = '172.30.77.57'

class color:
    """ Colors for text highlighting """
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
    """ 
        Commandline tool for listing and removing segments
    """
    prompt = f'{color.BOLD}{color.GREEN}nsx-t >{color.END} '

    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.auth()

    def auth(self):
        """
            The auth method is used to authenticate the user to access the NSX API.
            The user is prompted to enter the NSX API address, username, and password.
            The method attempts to establish a session by sending an HTTP GET request
            to the /api/v1/cluster/status endpoint using the given credentials.
            If the authentication fails due to an HTTP error or a connection error,
            then user will be asked for credentials again. 
        """
        self.segments = []
        authenticated = False  # Added a variable to track authentication status
        while not authenticated:
            self.api_url = "https://"
            self.api_url += input("NSX API Address: ")
            user = input("Username: ")
            password = getpass()
            self.session.auth = (user, password)
            try:
                response = self.session.get(f"{self.api_url}/api/v1/cluster/status", verify=False)
                response.raise_for_status()  # Added error handling
                authenticated = True  # Set authentication status to True if successful
            except requests.exceptions.HTTPError:
                print(f"{color.BOLD}{color.RED}Authentication failed!{color.END}")
            except requests.exceptions.ConnectionError:
                print(f"{color.BOLD}{color.RED}Failed to connect {self.api_url}!{color.END}")

    def remove_bindings(self, bindings: list[dict]) -> None:
        """
        The remove_bindings method takes in a list of binding dictionaries as input
        and removes all bindings maps for a profile using the NSX Policy API.
        """
        if bindings:
            for profile in bindings:
                path = profile["path"]
                res = self.session.delete(
                    f"{self.api_url}/policy/api/v1{path}",
                    verify=False
                )
                status = res.status_code
                print(f"Removing {path} - {status}")

    def get_segment(self, segment_id: str):
        """
        Get the segment by id
        """
        raw_segment = self.session.get(
            f"{self.api_url}/policy/api/v1/infra/segments/{segment_id}",
            verify=False
        )
        if raw_segment.status_code != 200:
            return None
        return json.loads(raw_segment.content)

    def get_segments(self) -> list[dict]:
        """ 
            Get all segments
        """
        raw_segments = self.session.get(
            f'{self.api_url}/policy/api/v1/infra/segments',
            verify=False
        )
        return json.loads(raw_segments.content).get("results", [])

    def get_logical_switches(self) -> dict:
        """
            Get logical switches
        """
        raw_logical_switches = self.session.get(
            f'{self.api_url}/api/v1/logical-switches',
            verify=False
        )
        return jq.first(
            '.results | map( { (.tags[]|select(.scope=="policyPath")|.tag): .id } ) | add',
            text=raw_logical_switches.content.decode()
        )

    def get_logical_ports(self) -> dict:
        """
        List of switches with logical ports
        """
        raw_logical_ports = self.session.get(
            f'{self.api_url}/api/v1/logical-ports',
            verify=False
        )
        pages = json.loads(raw_logical_ports.content)
        while pages.get("cursor"):
            raw_logical_ports = self.session.get(
                f'{self.api_url}/api/v1/logical-ports?cursor=' + pages["cursor"],
                verify=False
            )
            page = json.loads(raw_logical_ports.content)
            del pages["cursor"]
            if page.get("cursor"):
                pages["cursor"] = page["cursor"]
            if "results" in page.keys():
                pages["results"] += page["results"]
        return jq.first(
            '.results | map(select(.attachment.attachment_type=="VIF"))' +
            '| group_by(.logical_switch_id)' +
            '| map( { (.[0].logical_switch_id): map(.id) } ) | add',
            pages
        )

    def do_ls(self, line):
        """
        List and filter segments
        Use 'ls --help' to get some help
        """
        agparser = argparse.ArgumentParser(prog='ls')
        agparser.add_argument(
            "--detach",
            action='store_true',
            help='List detached segments' )
        agparser.add_argument(
            "--name", required=False,
            help='Filter output by display_name. Excpects regex' )
        agparser.add_argument(
            "--subnet",
            required=False,
            help='Filter output by subnet. Excpects regex' )
        agparser.add_argument(
            "--user",
            required=False,
            help='Filter output by user. Excpects regex' )
        try:
            args = agparser.parse_args(shlex.split(line))
        except SystemExit:
            return

        segments = self.get_segments()
        logical_switches = self.get_logical_switches()
        logical_ports = self.get_logical_ports()

        table = PrettyTable(['Name', 'ID', 'Ports', 'Subnets'])
        for segment in segments:
            decision = True
            nets = ""
            switch_id = logical_switches.get(segment["path"])
            ports = len(logical_ports.get(switch_id, []))
            if segment.get("subnets"):
                nets = ",".join([ net["network"] for net in segment["subnets"] ])
            if args:
                if args.name and not re.search(args.name, segment["display_name"]):
                    decision = False
                if args.subnet and not re.search(args.subnet, nets):
                    decision = False
                if args.user and not re.search(args.user, segment["_create_user"]):
                    decision = False
                if args.detach and ports != 0:
                    decision = False
            if decision:
                table.add_row( [ segment["display_name"], segment["id"], ports, nets ] )
        print(table)

    def do_rm(self, segment_id):
        """
            Remove a segment by ID
        """

        print( f'{color.BOLD}{color.RED}Removing {segment_id}...{color.END}' )

        segment = self.get_segment(segment_id)
        if not segment:
            print(f'Failed to get {segment_id}')
            return

        logical_ports = self.session.get(
            f'{self.api_url}/policy/api/v1/infra/segments/{segment_id}/ports/',
            verify=False
        )
        ports = json.loads(logical_ports.content).get("results")
        if ports and len(ports) > 0 :
            for port in ports:
                print(f"Detach port {port['display_name']}")
                self.session.post(
                    f'{self.api_url}/policy/api/v1/infra/realized-state/realized-entity?action=refresh&intent_path=/infra/segments/{segment_id}/ports/{port["unique_id"]}',
                    verify=False
                )
                self.session.get(
                    f'{self.api_url}/policy/api/v1/search?query=resource_type:SegmentPort AND path:"/infra/segments/{segment_id}/ports/{port["unique_id"]}"',
                    verify=False
                )
                self.session.delete(
                    f'{self.api_url}/api/v1/logical-ports/{port["unique_id"]}?detach=true',
                    verify=False
                )

        sdp_raw = self.session.get(
            f'{self.api_url}/policy/api/v1/infra/segments/{segment_id}/segment-discovery-profile-binding-maps',
            verify=False
        )
        self.remove_bindings(json.loads(sdp_raw.content).get("results"))

        ssp_raw = self.session.get(
            f'{self.api_url}/policy/api/v1/infra/segments/{segment_id}/segment-security-profile-binding-maps',
            verify=False
        )
        self.remove_bindings(json.loads(ssp_raw.content).get("results"))

        qos_raw = self.session.get(
            f'{self.api_url}/policy/api/v1/infra/segments/{segment_id}/segment-qos-profile-binding-maps',
            verify=False
        )
        self.remove_bindings(json.loads(qos_raw.content).get("results"))

        seg = self.session.delete(f'{self.api_url}/policy/api/v1/infra/segments/{segment_id}', verify=False)

        if seg.status_code == 200:
            print(f'{segment_id} is deleted')
        else:
            print(f'Failed to delete {segment_id}!')
            error = json.loads(seg.content)
            print(json.dumps(error, indent=4))

    def do_rm_by(self, line):
        """
            Remove a group of segments by regex
        """
        agparser = argparse.ArgumentParser(prog='rm_by')
        agparser.add_argument("--name", required=False, help='Filter output by display_name. Excpects regex')
        agparser.add_argument("--id", required=False, help='Filter output by id. Excpects regex')
        agparser.add_argument("--detach", action='store_true', help='Filter detached segments')

        try:
            args = agparser.parse_args(shlex.split(line))
        except SystemExit:
            return

        segments = self.get_segments()
        for segment in segments:
            if re.search(args.name, segment["display_name"]):
                self.do_rm(segment["id"])

    def do_describe(self, segment_id):
        """
        Show info about a segment and its connected ports
        """
        segment = self.get_segment(segment_id)
        if not segment:
            print("The segment was not found")
            return

        # Print INFO about the segment
        print(f'{color.BOLD}Display name:{color.END} {segment["display_name"]}')
        print(f'{color.BOLD}ID:{color.END} {segment_id}')
        print(f'{color.BOLD}Cretaed by:{color.END} {segment["_create_user"]}')

        # Print INFO about the ports
        logical_ports = self.session.get(
            f'{self.api_url}/policy/api/v1/infra/segments/{segment_id}/ports/',
            verify=False
        )
        ports = json.loads(logical_ports.content).get("results")
        table = PrettyTable(['ID', 'NAME', 'Status'])
        if len(ports) > 0 :
            for port in ports:
                # Refresh info about the port and get its status
                # The port can be attached to VM which does not exists
                self.session.post(
                    f'{self.api_url}/policy/api/v1/infra/realized-state/realized-entity?action=refresh&intent_path=/infra/segments/{segment_id}/ports/{port["id"]}',
                    verify=False
                )
                port_state_raw = self.session.get(
                    f'{self.api_url}/policy/api/v1/search?query=resource_type:SegmentPort AND path:"/infra/segments/{segment_id}/ports/{port["id"]}"',
                    verify=False
                )
                port_state = json.loads(port_state_raw.content).get("results")
                status = port_state[0]["status"]["consolidated_status"]["consolidated_status"]
                table.add_row( [ port["unique_id"], port["display_name"], status ] )
        print(table)

    def do_EOF(self, line):
        """
            If a command handler returns a true value, the program will exit cleanly
        """
        return True

if __name__ == '__main__':
    NSX().cmdloop()
