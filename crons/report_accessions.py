import datetime
import logging
from pathlib import Path

from .as_cron import BaseAsCron
from .helpers import formula_to_string, get_fiscal_year


class AccessionsReporter(BaseAsCron):
    def __init__(self):
        super(AccessionsReporter, self).__init__("report_accessions_sheet")
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
            "created at",
            "modified at",
            "modified by",
        ]

    def create_report(self, google=False):
        repositories = {"rbml": 2, "avery": 3, "rbmlbooks": 6, "ohac": 7}
        for name, repo_id in repositories.items():
            self.construct_sheet(name, repo_id, google=google)
        msg = f"Accession records imported by {__file__}."
        return msg

    def construct_sheet(self, name, repo_id, google=False):
        spreadsheet_data = self.get_sheet_data(repo_id)
        rows_count = len(spreadsheet_data) - 1
        if google:
            self.write_data_to_google_sheet(
                spreadsheet_data,
                self.config["Google Sheets"]["report_accessions_sheet"],
                f"{name}!A:Z",
            )
        else:
            csv_filename = f"{datetime.datetime.now().strftime('%Y_%m_%d_%H%M')}_{Path(__file__).resolve().name.split('.')[0]}_{name}.csv"
            csv_filepath = Path(self.config["CSV"]["outpath"], csv_filename)
            self.write_data_to_csv(spreadsheet_data, csv_filepath)
        msg = f"{rows_count} records imported by {__file__}."
        logging.info(msg)
        return msg

    def get_sheet_data(self, repo_id):
        spreadsheet_data = []
        spreadsheet_data.append(self.fields)
        rows_data = self.get_row_data(repo_id)
        for r in rows_data:
            resource_row = self.construct_row(r)
            spreadsheet_data.append(resource_row)
        return spreadsheet_data

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
            if accession.get("related_resources"):
                resource = self.as_client.get_json_response(
                    accession["related_resources"][0]["ref"]
                )
            else:
                resource = None
            accession_fields = {
                "repository": accession["repository"]["ref"],
                "uri": accession["uri"],
                "title": accession["title"].strip(),
                "accession_date": accession.get("accession_date"),
                "id_0": accession.get("id_0"),
                "id_1": accession.get("id_1"),
                "id_2": accession.get("id_2"),
                "id_3": formula_to_string(accession.get("id_3"))
                if accession.get("id_3")
                else "",
                "integer_1": accession.get("integer_1"),
                "created at": accession["create_time"],
                "modified at": accession["system_mtime"],
                "created by": accession["created_by"],
                "modified by": accession["last_modified_by"],
                "resource_bibid": resource["id_0"] if resource else "",
                "resource_asid": resource["uri"] if resource else "",
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
