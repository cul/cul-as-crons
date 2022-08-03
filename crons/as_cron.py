from configparser import ConfigParser
from datetime import datetime

from .aspace_client import ArchivesSpaceClient
from .digester import Digester
from .google_sheets_client import DataSheet


class BaseAsCron(object):
    """Base class which all crons inherit.

    Subclasses should implement a `get_as_data` method.
    """

    def __init__(self, config_file, log_name, sheet_name):
        """Set up configs and logging.

        Args:
            config_file: path to config file
            log_name: path to log file
            sheet_name: key from config that corresponds to a Google Sheet
        """
        self.config = ConfigParser()
        self.config.read(config_file)
        self.as_client = ArchivesSpaceClient(
            self.config["ArchivesSpace"]["baseurl"],
            self.config["ArchivesSpace"]["username"],
            self.config["ArchivesSpace"]["password"],
        )
        self.google_token = self.config["Google Sheets"]["token"]
        self.google_sheet = self.config["Google Sheets"][sheet_name]
        self.log_sheet = DataSheet(self.google_token, self.google_sheet, "log!A:A")
        self.exit_msg = f"Script done. Updated data is available at https://docs.google.com/spreadsheets/d/{self.google_sheet}/edit?usp=sharing"

    def run(self):
        start_time = datetime.now()
        get_as_data = self.get_as_data()
        end_time = datetime.now()
        msg_duration = f"Start: {start_time}. Finished: {end_time} (duration: {end_time - start_time})"
        msg = f"{get_as_data} {msg_duration}"
        Digester(self.config_file).post_digest(__file__, self.exit_msg)
        self.log_sheet.append_sheet([msg])
        return msg

    def get_as_data(self):
        raise NotImplementedError("You must implement a `get_as_data` method")
