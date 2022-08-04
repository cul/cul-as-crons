import logging

from .as_cron import BaseAsCron
from .google_sheets_client import DataSheet


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
        self.data_sheet = DataSheet(
            self.google_token,
            self.google_sheet,
            self.config["Google Sheets"]["report_subjects_range"],
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

    def get_as_data(self):
        self.data_sheet.clear_sheet
        spreadsheet_data = []
        spreadsheet_data.append([x[0] for x in self.fields])
        subject_records = self.as_client.all_subjects()
        for subject in subject_records:
            row = self.get_row(subject)
            spreadsheet_data.append(row)
        subject_count = len(spreadsheet_data) - 1
        logging.info(f"Total subject records: {subject_count}")
        self.data_sheet.append_sheet(spreadsheet_data)
        logging.info(
            f"{len(spreadsheet_data)} rows written to {self.data_sheet.spreadsheet_id}"
        )
        msg = f"{subject_count} records imported by {__file__}."
        return msg

    def get_row(self, subject_record):
        row = []
        for field in [x[1] for x in self.fields]:
            row.append(subject_record.get(field))
        if subject_record.get("terms"):
            for term in subject_record.get("terms"):
                row.append("{} [{}]".format(term["term"], term["term_type"]))
        return row