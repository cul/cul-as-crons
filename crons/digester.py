import logging
from configparser import ConfigParser
from datetime import datetime, timedelta
from itertools import groupby
from os.path import basename

from dateutil.parser import parse

from .google_sheets_client import DataSheet


class Digester(object):
    """Log results from other scripts to sheet and send results based on date to email.

    Relies on a Google Sheet with log data. Call post_digest() from other scripts to
    add to log. Call run() to generate report, e.g., for daily digest email. Set
    garbage_day to day of month on which to perform cleanup.
    """

    def __init__(self, config_file, test=False):
        self.config = ConfigParser()
        self.config.read(config_file)
        logging.basicConfig(
            datefmt="%m/%d/%Y %I:%M:%S %p",
            format="%(asctime)s %(message)s",
            level=logging.INFO,
            handlers=[logging.FileHandler("digester.log"), logging.StreamHandler()],
        )
        self.garbage_day = 15  # Day of month to prune old entries from sheet
        google_token = self.config["Google Sheets"]["token"]
        if test:
            google_sheet = self.config["Google Sheets"]["digester_test_sheet"]
        else:
            google_sheet = self.config["Google Sheets"]["digester_sheet"]
        self.data_sheet = DataSheet(
            google_token, google_sheet, self.config["Google Sheets"]["digester_range"]
        )

    def run(self):
        """Generate report, e.g., for daily digest email."""
        now = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        if datetime.today().day == self.garbage_day:
            logging.info("Cleaning up old digest entries...")
            logging.info(self.cleanup_datasheet())
        logging.info(
            f"This 24-hour digest composed at {now} by {basename(__file__)}. Contact asops@library.columbia.edu with questions/problems."
        )
        for s in self.get_digest():
            logging.info(f"\n\U000025B6 *** OUTPUT FROM {s['script']} ***")
            for m in s["msg"]:
                logging.info("• {m['value']}")
            logging.info("******************\n")

    def cleanup_datasheet(self, date_column=1, month_offset=2):
        """Prune log sheet to recent entries (by month).

        By default, remove all rows except from current and previous month.

        Args:
            date_column (int, optional): Column index where date is found.
            month_offset (int, optional): Number of months to include. 2 will include current and previous month.

        Returns:
            str: message
        """
        sheet_data = self.data_sheet.get_sheet_data()
        month_diff = datetime.today().month - month_offset
        new_data = [
            row for row in sheet_data if parse(row[date_column]).month > month_diff
        ]
        if len(new_data) > 0:
            self.data_sheet.clear_sheet()
            self.data_sheet.append_sheet(new_data)
            msg = f"{len(sheet_data) - len(new_data)} removed. {len(new_data)} recent entries retained."
        else:
            msg = "0 entries removed."
        return msg

    def get_digest(self):
        """Get digest-formatted output from log sheet.

        Returns:
            list: List of log entries (dicts), aggregated daily by script name
        """
        data = self.data_sheet.get_sheet_data()
        the_msg_data = []
        for row in data:
            date = parse(row[1])
            if date > (datetime.now() - timedelta(days=1)):
                the_msg_data.append((row[0], date, row[2]))
        the_result = []
        for key, group in groupby(sorted(the_msg_data), lambda x: x[0]):
            # Return a dict of values with timestamps grouped by script.
            r = {"script": key, "msg": [{"time": m[1], "value": m[2]} for m in group]}
            the_result.append(r)
            # Sort the results reverse chronologically.
            the_result.sort(key=lambda x: x["msg"][0]["time"], reverse=True)
        return the_result

    def post_digest(self, script_name, log, truncate=40000):
        """Add a digest record to log sheet.

        Args:
            script_name (str): filename of generating script
            log (str): Log text
            truncate (int, optional): Max length of log entry. Defaults to 40000.

        Returns:
            str: JSON response of POST to sheet.
        """
        if len(log) > truncate:
            log = f"{log[:truncate]} [...]"
        data = [[script_name, str(datetime.today()), log]]
        return self.data_sheet.append_sheet(data)
