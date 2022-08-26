import logging

from .as_cron import BaseAsCron
from .google_sheets_client import DataSheet


class AgentsReporter(BaseAsCron):
    def __init__(self, config_file):
        super(AgentsReporter, self).__init__(config_file, "report_agents_sheet")
        logging.basicConfig(
            datefmt="%m/%d/%Y %I:%M:%S %p",
            format="%(asctime)s %(message)s",
            level=logging.INFO,
            handlers=[
                logging.FileHandler("agents_reporter.log"),
                logging.StreamHandler(),
            ],
        )
        self.fields = [
            "uri",
            "title",
            "source",
            "authority_id",
            "is_linked_to_published_record",
            "publish",
            "last_modified_by",
            "last_modified",
        ]

    def get_sheet_data(self):
        spreadsheet_data = []
        spreadsheet_data.append(self.fields)
        agent_data = self.get_row_data()
        for agent in agent_data:
            agent_row = self.construct_row(agent)
            spreadsheet_data.append(agent_row)
        agent_count = len(spreadsheet_data) - 1
        logging.info(f"Total agent records: {agent_count}")
        self.write_data_to_sheet(spreadsheet_data)
        msg = f"{agent_count} records imported by {__file__}."
        return msg

    def write_data_to_sheet(self, sheet_data):
        data_sheet = DataSheet(
            self.google_access_token,
            self.google_refresh_token,
            self.google_client_id,
            self.client_secret,
            self.config["Google Sheets"]["report_agents_sheet"],
            self.config["Google Sheets"]["report_agents_range"],
        )
        data_sheet.clear_sheet()
        data_sheet.append_sheet(sheet_data)
        return f"Posted {len(sheet_data)} rows to sheet."

    def construct_row(self, row_data):
        """Construct row to write to spreadsheet.

        Args:
            row_data (dict): data from ASpace to write to row

        Returns:
            list: ordered fields
        """
        return [row_data[field] for field in self.fields]

    def get_row_data(self):
        for agent in self.as_client.all_agents():
            agent_fields = {
                "uri": agent["uri"],
                "title": agent["title"],
                "source": agent.get("names")[0].get("source"),
                "authority_id": agent.get("names")[0].get("authority_id"),
                "is_linked_to_published_record": agent["is_linked_to_published_record"],
                "publish": agent["publish"],
                "last_modified_by": agent["last_modified_by"],
                "last_modified": agent["system_mtime"],
            }
            yield agent_fields
