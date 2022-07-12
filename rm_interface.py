import asyncio
import configparser
import logging
import traceback
import json

import humanize
import qbittorrent.client
from qbittorrent import Client

from inhibitor_plugin import InhibitorPlugin
from torrent_formatter import torrent_format

logging.getLogger(__name__).setLevel(logging.DEBUG)


class RainMeterInterface:

    def __init__(self, rainmeter):
        self.version = "v1.3"
        self.rainmeter = rainmeter
        self.running = True
        self.rainmeter_lock = asyncio.Lock()
        self.torrents = {}
        self.rainmeter_values = {}
        self.torrent_progress = ""

        ini = self.rainmeter.RmGetSkinName()
        ini_parser = configparser.ConfigParser()
        ini_parser.read(ini)
        self.rainmeter_meters = [x for x in ini_parser.sections() if "Torrent" in x and "Measure" not in x]

        self.rainmeter.RmExecute(f"[!SetOption Title Text \"BlockBust Viewer {self.version}\"]")

        self.page_start = 0
        self.torrent_num = 0
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
        self.qb_user = secrets['Username']
        self.qb_pass = secrets['Password']
        self.qb_host = secrets['Host']
        self.qb = Client(self.qb_host)
        self.qb_connected = False
        self.qb = None
        self.qb_data = {}
        self.inhibitor_plugin = InhibitorPlugin(url="localhost", main_port=47675, alt_port=47676)
        self.inhibitor_plug_task = asyncio.create_task(self.inhibitor_plugin.run())
        self.refresh_task = asyncio.create_task(self.refresh_torrents())

    def _connect(self):
        try:
            self.qb.login(self.qb_user, self.qb_pass)
            self.qb_connected = True
        except Exception as e:
            logging.critical(f"Unable to connect to server {e}\n{traceback.format_exc()}")
            self.qb_connected = False

    async def refresh_torrents(self):
        while self.running:
            try:
                if not self.qb_connected:
                    self._connect()
                try:
                    torrents = self.qb.torrents()
                    qb_data = self.qb.sync_main_data()
                    self.qb_data['url'] = self.qb.url.split("/")[2]
                    self.qb_data['version'] = self.qb.qittorrent_version
                except qbittorrent.client.LoginRequired:
                    self.qb_connected = False
                else:
                    self.qb_data['free_space'] = qb_data['server_state']['free_space_on_disk']
                    self.qb_data['global_dl'] = qb_data['server_state']['dl_info_speed']
                    self.qb_data['global_up'] = qb_data['server_state']['up_info_speed']
                    self.qb_data['total_peers'] = qb_data['server_state']['total_peer_connections']
                    torrents = sorted(torrents, key=lambda d: d['added_on'])
                    torrents.reverse()
                    self.torrent_num = len(torrents)
                    self.torrents = torrents
                    await self.parse_rm_values()
                    await asyncio.sleep(2)
            except Exception as e:
                logging.error(f"Failed to get torrents: {e}")
                await asyncio.sleep(5)

    async def parse_rm_values(self):
        async with self.rainmeter_lock:
            torrents = self.torrents[self.page_start:self.page_start + 4]
            tprogress = {'progress': []}
            for torrent in torrents:
                tprogress['progress'].append(torrent['progress'] * 100.0)
            self.torrent_progress = json.dumps(tprogress)
            self.rainmeter_values = torrent_format(torrents)
            self.rainmeter_values['InhibitorMeter']['Text'] = await self.inhibitor_plugin.get_inhibitor_status()
            self.rainmeter_values['ConnectionMeter']['Text'] = \
                "Connected to " + self.qb_data['url'] + "  qBittorrent " + self.qb_data['version']
            if self.inhibitor_plugin.get_inhibitor_state():
                self.rainmeter_values['PlayButton']['Hidden'] = "0"
                self.rainmeter_values['PauseButton']['Hidden'] = "1"
            else:
                self.rainmeter_values['PlayButton']['Hidden'] = "1"
                self.rainmeter_values['PauseButton']['Hidden'] = "0"
            self.rainmeter_values['GlobalDownload']['Text'] = f"DL: {humanize.naturalsize(self.qb_data['global_dl'])}/s"
            self.rainmeter_values['GlobalUpload']['Text'] = f"UP: {humanize.naturalsize(self.qb_data['global_up'])}/s"
            self.rainmeter_values['GlobalPeers']['Text'] = f"Connected peers: {self.qb_data['total_peers']}"
            self.rainmeter_values['FreeSpace']['Text'] = \
                f"Free space: {humanize.naturalsize(self.qb_data['free_space'])}"

    async def update(self):
        """Called by the rainmeter plugin to update the display"""

        for meter in self.rainmeter_meters:
            async with self.rainmeter_lock:
                for key, value in self.rainmeter_values[meter]:
                    self.rainmeter.RmExecute(f"[!SetOption {meter} {key} \"{value}\"")

    def get_string(self) -> str:
        """Called by the rainmeter plugin to get the current display string"""
        return self.torrent_progress

    async def execute_bang(self, bang):
        """Called by the rainmeter plugin"""
        pass

    async def tear_down(self):
        """Call this when the plugin is being unloaded"""
        pass
