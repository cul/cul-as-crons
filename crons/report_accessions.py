import datetime
import logging

from .as_cron import BaseAsCron
from .google_sheets_client import DataSheet
from .helpers import get_fiscal_year


class AccessionsReporter(BaseAsCron):
    def __init__(self, config_file):
        super(AccessionsReporter, self).__init__(config_file, "report_accessions_sheet")
        logging.basicConfig(
            datefmt="%m/%d/%Y %I:%M:%S %p",
            format="%(asctime)s %(message)s",
            level=logging.INFO,
            handlers=[
                logging.FileHandler("accessions_reporter.log"),
                logging.StreamHandler(),
            ],
        )
        self.fields = [
            "title",
            "uri",
            "accession_date",
            "id_0",
            "id_1",
            "id_2",
            "id_3",
            "integer_1",
            "resource_bibid",
            "resource_asid",
            "repo",
            "year",
            "fiscal-year",
            "processing_priority",
            "processing_status",
            "create_time",
            "system_mtime",
            "last_modified_by",
        ]

    def get_sheet_data(self):
        repositories = {"rbml": 2, "avery": 3, "rbmlbooks": 6}
        for name, repo_id in repositories.items():
            self.construct_sheet(name, repo_id)
        msg = f"Accession records imported by {__file__}."
        return msg

    def construct_sheet(self, name, repo_id):
        spreadsheet_data = []
        spreadsheet_data.append(self.fields)
        rows_data = self.get_row_data(repo_id)
        for r in rows_data:
            resource_row = self.construct_row(r)
            spreadsheet_data.append(resource_row)
        msg = self.write_data_to_sheet(spreadsheet_data, f"{name}!A:Z")
        logging.info(msg)
        return msg

    def write_data_to_sheet(self, sheet_data, data_range):
        data_sheet = DataSheet(
            self.google_access_token,
            self.google_refresh_token,
            self.google_client_id,
            self.client_secret,
            self.config["Google Sheets"]["report_accessions_sheet"],
            data_range,
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
        return [row_data.get(field) for field in self.fields]

    def get_row_data(self, repo_id):
        """Get accession data to be written into a row.

        Args:
            repo_id (int): ASpace repository ID (e.g., 2)

        Yields:
            dict
        """
        one_week_ago = datetime.date.today() - datetime.timedelta(7)
        for accession in self.as_client.accessions_from_repository(repo_id):
            y, m, d = (int(a) for a in accession["accession_date"].split("-"))
            accession_date = datetime.date(y, m, d)
            resource = self.as_client.get_json_response(
                accession["related_resources"][0]["ref"]
            )
            accession_fields = {
                "repository": accession["repository"]["ref"],
                "uri": accession["uri"],
                "title": accession["title"].strip(),
                "accession_date": accession.get("accession_date"),
                "id_0": accession.get("id_0"),
                "id_1": accession.get("id_1"),
                "id_2": accession.get("id_2"),
                "id_3": accession.get("id_3"),
                "integer_1": accession.get("integer_1"),
                "created at": accession["create_time"],
                "modified at": accession["system_mtime"],
                "created by": accession["created_by"],
                "modified by": accession["last_modified_by"],
                "resource_bibid": resource["id_0"],
                "resource_asid": resource["uri"],
                "year": y if y > 1700 else "",
                "fiscal_year": get_fiscal_year(accession_date),
                "processing_status": accession.get("collection_management").get(
                    "processing_status"
                )
                if accession.get("collection_management")
                else "",
                "processing_priority": accession.get("collection_management").get(
                    "processing_priority"
                )
                if accession.get("collection_management")
                else "",
                "recent": True if accession_date > one_week_ago else False,
                "extents": self.as_client.get_extents(accession),
            }
            yield accession_fields