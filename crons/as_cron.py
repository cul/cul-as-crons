from configparser import ConfigParser
from datetime import datetime

from .aspace_client import ArchivesSpaceClient
from .google_sheets_client import DataSheet


class BaseAsCron(object):
    """Base class which all ArchivesSpace crons inherit.

    Subclasses should implement a `get_sheet_data` method.
    """

    def __init__(self, config_file, sheet_name):
        """Set up configs and logging.

        Args:
            config_file: path to config file
            log_name: path to log file
            sheet_name: key from config that corresponds to a Google Sheet
        """
        self.config_file = config_file
        self.config = ConfigParser()
        self.config.read(self.config_file)
        self.as_client = ArchivesSpaceClient(
            self.config["ArchivesSpace"]["baseurl"],
            self.config["ArchivesSpace"]["username"],
            self.config["ArchivesSpace"]["password"],
        )
        self.google_access_token = self.config["Google Sheets"]["access_token"]
        self.google_refresh_token = self.config["Google Sheets"]["refresh_token"]
        self.google_client_id = self.config["Google Sheets"]["client_id"]
        self.client_secret = self.config["Google Sheets"]["client_secret"]

    def run(self):
        start_time = datetime.now()
        get_sheet_data = self.get_sheet_data()
        end_time = datetime.now()
        msg_duration = f"Start: {start_time}. Finished: {end_time} (duration: {end_time - start_time})"
        msg = f"{get_sheet_data} {msg_duration}"
        return msg

    def construct_row(self, row_data):
        """Construct row to write to spreadsheet.

        Args:
            row_data (dict): data from ASpace to write to row

        Returns:
            list: ordered fields
        """
        return [row_data.get(field) for field in self.fields]

    def write_data_to_sheet(self, sheet_data, sheet_id, data_range):
        """Write data to a Google Sheet.

        Args:
            sheet_data (list): list of lists (rows)
            sheet_id: Google Sheet ID
            data_range: the A1 notation of a range for a logical table of data
        """
        data_sheet = DataSheet(
            self.google_access_token,
            self.google_refresh_token,
            self.google_client_id,
            self.client_secret,
            sheet_id,
            data_range,
        )
        data_sheet.clear_sheet()
        data_sheet.append_sheet(sheet_data)
        return f"Posted {len(sheet_data)} rows to sheet."

    def get_sheet_data(self):
        raise NotImplementedError("You must implement a `get_sheet_data` method")
