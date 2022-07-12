import asyncio
import configparser
import logging
import traceback
import json
import os

import humanize
import qbittorrent.client
from qbittorrent import Client

from inhibitor_plugin import InhibitorPlugin
from torrent_formatter import torrent_format

logging.getLogger(__name__).setLevel(logging.DEBUG)


class RainMeterInterface:

    def __init__(self, rainmeter, event_loop):
        try:
            logging.debug(f"Initial working directory: {os.getcwd()}")
            os.chdir(os.path.dirname(os.path.abspath(__file__)))
            logging.debug(f"Changed working directory to: {os.getcwd()}")

            logging.debug("Initializing RainMeterInterface")
            self.version = "v2.0"
            self.rainmeter = rainmeter
            self.event_loop = event_loop

            self.running = True
            self.torrents = {}
            self.rainmeter_values = {}
            self.torrent_progress = ""

            # ini_parser = configparser.ConfigParser()
            # logging.info("Loading qbt_ini.ini")
            # ini_parser.read(r"..\..\qbt_ini.ini")
            # logging.info("qbt_ini.ini loaded")

            # self.rainmeter_meters = \
            #     [x for x in ini_parser.sections() if "Torrent" in x and "Measure" not in x and "style" not in x]

            # self.rainmeter.RmExecute(f"[!SetOption Title Text \"BlockBust Viewer {self.version}\"]")

            self.page_start = 0
            self.torrent_num = 0
            logging.debug("Loading secrets.json")
            with open(r"C:\Users\Aidan\Documents\Rainmeter\Skins\qbt_widgetv2\@Resources\Scripts\secrets.json",
                      "r") as secrets_file:
                secrets = json.load(secrets_file)
            logging.debug("secrets.json loaded")
            self.qb_user = secrets['Username']
            self.qb_pass = secrets['Password']
            self.qb_host = secrets['Host']
            self.qb = Client(self.qb_host)
            self.qb_connected = False
            self.qb_data = {}
            logging.debug("Launching background tasks")
            self.inhibitor_plugin = InhibitorPlugin(url="1", main_port=47675, alt_port=47676)
            self.rainmeter.RmLog(self.rainmeter.LOG_NOTICE, "Launching background tasks")
            self.inhibitor_plug_task = self.event_loop.create_task(self.inhibitor_plugin.run(self.event_loop))
            self.refresh_task = self.event_loop.create_task(self.refresh_torrents())
            logging.debug("Background tasks launched")
            self.refresh_task.add_done_callback(self._on_refresh_task_finished)
            logging.debug("Background tasks launched")
        except Exception as e:
            logging.critical(f"Unable to initialize RainMeterInterface: {e}\n{traceback.format_exc()}")

    def _on_refresh_task_finished(self):
        self.rainmeter.RmLog(self.rainmeter.LOG_NOTICE, "Refresh task finished")
        logging.critical("Refresh task finished")

    def _connect(self):
        try:
            self.qb.login(self.qb_user, self.qb_pass)
            self.qb_connected = True
        except Exception as e:
            logging.critical(f"Unable to connect to server {e}\n{traceback.format_exc()}")
            self.rainmeter.RmLog(self.rainmeter.LOG_ERROR, f"Unable to connect to server {e}")
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
                    self.qb_data['version'] = self.qb.qbittorrent_version
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
            except Exception as e:
                logging.error(f"Failed to get torrents: {e}\n{traceback.format_exc()}")
                await asyncio.sleep(5)
            finally:
                await self.parse_rm_values()
                await asyncio.sleep(2)

    async def parse_rm_values(self):
        """Parse the rainmeter values"""
        logging.info("Parsing rainmeter values")
        try:
            torrents = self.torrents[self.page_start:self.page_start + 4]
            tprogress = {'progress': []}
            for torrent in torrents:
                tprogress['progress'].append(torrent['progress'] * 100.0)
            self.torrent_progress = json.dumps(tprogress)
            self.rainmeter_values = torrent_format(torrents)
            self.rainmeter_values['Title'] = {'Text': "BlockBust Viewer " + self.version}
            self.rainmeter_values['ConnectionMeter'] = {'Text': "Connected to " + self.qb_data['url'] +
                                                                "  qBittorrent " + self.qb_data['version']}
            if self.inhibitor_plugin.get_inhibitor_state():
                self.rainmeter_values['PlayButton'] = {'Hidden': "0"}
                self.rainmeter_values['PauseButton'] = {'Hidden': "1"}
            else:
                self.rainmeter_values['PlayButton'] = {'Hidden': "1"}
                self.rainmeter_values['PauseButton'] = {'Hidden': "0"}
            self.rainmeter_values['GlobalDownload'] = {
                'Text': f"DL: {humanize.naturalsize(self.qb_data['global_dl'])}/s"}
            self.rainmeter_values['GlobalUpload'] = {
                'Text': f"UP: {humanize.naturalsize(self.qb_data['global_up'])}/s"}
            self.rainmeter_values['GlobalPeers'] = {'Text': f"Connected peers: {self.qb_data['total_peers']}"}
            self.rainmeter_values['FreeSpace'] = \
                {'Text': f"Free space: {humanize.naturalsize(self.qb_data['free_space'])}"}
            self.rainmeter_values['InhibitorMeter'] = {'Text': await self.inhibitor_plugin.get_inhibitor_status()}
        except Exception as e:
            logging.error(f"Failed to parse rainmeter values: {e}\n{traceback.format_exc()}")
        else:
            bang = ""
            for meter in self.rainmeter_values.keys():
                for key, value in self.rainmeter_values[meter].items():
                    bang += f"[!SetOption {meter} {key} \"{value}\"]"
            self.rainmeter.RmExecute(bang)

    def get_string(self) -> str:
        """Called by the rainmeter plugin to get the current display string"""
        return self.torrent_progress

    async def execute_bang(self, bang):
        """Called by the rainmeter plugin"""
        pass

    async def tear_down(self):
        """Call this when the plugin is being unloaded"""
        pass
