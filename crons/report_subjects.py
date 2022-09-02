import logging
from datetime import datetime
from pathlib import Path

from .as_cron import BaseAsCron


class SubjectReporter(BaseAsCron):
    def __init__(self, config_file):
        super(SubjectReporter, self).__init__(config_file, "report_subjects_sheet")
        logging.basicConfig(
            datefmt="%m/%d/%Y %I:%M:%S %p",
            format="%(asctime)s %(message)s",
            level=logging.INFO,
            handlers=[
                logging.FileHandler("subject_reporter.log"),
                logging.StreamHandler(),
            ],
        )
        self.fields = [
            ("uri", "uri"),
            ("title", "title"),
            ("source", "source"),
            ("authority_id", "authority_id"),
            ("is_linked_to_published_record", "is_linked_to_published_record"),
            ("publish", "publish"),
            ("last_modified_by", "last_modified_by"),
            ("last_modified", "system_mtime"),
        ]

    def create_report(self, google=False):
        spreadsheet_data = self.get_sheet_data()
        subject_count = len(spreadsheet_data) - 1
        logging.info(f"Total subject records: {subject_count}")

        if google:
            self.write_data_to_google_sheet(
                spreadsheet_data,
                self.config["Google Sheets"]["report_subjects_sheet"],
                self.config["Google Sheets"]["report_subjects_range"],
            )
        else:
            csv_filename = f"{datetime.now().strftime('%Y_%m_%d_%H%M')}_{Path(__file__).resolve().name.split('.')[0]}.csv"
            csv_filepath = Path(self.config["CSV"]["outpath"], csv_filename)
            self.write_data_to_csv(spreadsheet_data, csv_filepath)
        msg = f"{subject_count} records imported by {__file__}."
        return msg

    def get_sheet_data(self):
        spreadsheet_data = []
        spreadsheet_data.append(self.fields)
        subject_data = self.get_row_data()
        for subject in subject_data:
            subject_row = self.construct_row(subject)
            spreadsheet_data.append(subject_row)
        return spreadsheet_data

    def get_row(self, subject_record):
        row = []
        for field in [x[1] for x in self.fields]:
            row.append(subject_record.get(field))
        if subject_record.get("terms"):
            for term in subject_record.get("terms"):
                row.append("{} [{}]".format(term["term"], term["term_type"]))
        return row

    def get_row_data(self):
        """Get subject data to be written into a row.

        Yields:
            dict
        """
        for subject in self.as_client.all_subjects():
            subject_fields = {
                "uri": subject["uri"],
                "title": subject["title"],
                "source": subject["source"],
                "authority_id": subject["authority_id"],
                "is_linked_to_published_record": subject[
                    "is_linked_to_published_record"
                ],
                "publish": subject["publish"],
                "last_modified_by": subject["last_modified_by"],
                "last_modified": subject["system_mtime"],
            }
            yield subject_fields
