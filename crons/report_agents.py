import logging

from .as_cron import BaseAsCron
from .google_sheets_client import DataSheet


class AgentsReporter(BaseAsCron):
    def __init__(self, config_file):
        super(AgentsReporter, self).__init__(config_file, "report_subjects_sheet")
        logging.basicConfig(
            datefmt="%m/%d/%Y %I:%M:%S %p",
            format="%(asctime)s %(message)s",
            level=logging.INFO,
            handlers=[
                logging.FileHandler("agents_reporter.log"),
                logging.StreamHandler(),
            ],
        )
        self.data_sheet = DataSheet(
            self.google_token,
            self.google_sheet,
            self.config["Google Sheets"]["report_agents_range"],
        )

    def get_as_data(self):
        self.data_sheet.clear_sheet
        spreadsheet_data = []
        spreadsheet_data.append(self.fields)
        agent_rows = self.get_row_data()
        for agent_row in agent_rows:
            spreadsheet_data.append(agent_row)
        subject_count = len(spreadsheet_data) - 1
        logging.info(f"Total agent records: {subject_count}")
        self.data_sheet.append_sheet(spreadsheet_data)
        logging.info(
            f"{len(spreadsheet_data)} rows written to {self.data_sheet.spreadsheet_id}"
        )
        msg = f"{subject_count} records imported by {__file__}."
        return msg

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
