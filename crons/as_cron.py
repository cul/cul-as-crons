import csv
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path

from .aspace_client import ArchivesSpaceClient
from .google_sheets_client import DataSheet


class BaseAsCron(object):
    """Base class which all ArchivesSpace crons inherit.

    Subclasses should implement a `get_sheet_data` method.
    """

    def __init__(self, sheet_name):
        """Set up configs and logging.

        Args:
            config_file: path to config file
            log_name: path to log file
            sheet_name: key from config that corresponds to a Google Sheet
        """
        current_path = Path(__file__).parents[1].resolve()
        self.config_file = Path(current_path, "local_settings.cfg")
        self.config = ConfigParser()
        self.config.read(self.config_file)
        self.as_client = ArchivesSpaceClient(
            self.config["ArchivesSpace"]["baseurl"],
            self.config["ArchivesSpace"]["username"],
            self.config["ArchivesSpace"]["password"],
        )
        self.google_access_token = None
        self.google_refresh_token = self.config["Google Sheets"]["refresh_token"]
        self.google_client_id = self.config["Google Sheets"]["client_id"]
        self.client_secret = self.config["Google Sheets"]["client_secret"]

    def run(self, google=False):
        start_time = datetime.now()
        report = self.create_report(google=google)
        end_time = datetime.now()
        msg_duration = f"Start: {start_time}. Finished: {end_time} (duration: {end_time - start_time})"
        msg = f"{report} {msg_duration}"
        return msg

    def construct_row(self, row_data):
        """Construct row to write to spreadsheet.

        Args:
            row_data (dict): data from ASpace to write to row

        Returns:
            list: ordered fields
        """
        return [row_data.get(field) for field in self.fields]

    def write_data_to_google_sheet(self, sheet_data, sheet_id, data_range):
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
        return f"Posted {len(sheet_data)} rows to https://docs.google.com/spreadsheets/d/{sheet_id}"

    def write_data_to_csv(self, sheet_data, filepath):
        """Write data to a CSV file.

        Args:
            sheet_data (list): list of lists (rows)
            filepath (Path obj or str): Path object or string of CSV filepath
        """
        with open(filepath, "w") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(sheet_data)
        return f"Wrote {len(sheet_data)} rows to {filepath}"

    def create_report(self):
        raise NotImplementedError("You must implement a `create_report` method")
