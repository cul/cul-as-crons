import logging

from .as_cron import BaseAsCron
from .google_sheets_client import DataSheet


class ResourceReporter(BaseAsCron):
    def __init__(self, config_file):
        super(ResourceReporter, self).__init__(config_file, "report_resources_sheet")
        logging.basicConfig(
            datefmt="%m/%d/%Y %I:%M:%S %p",
            format="%(asctime)s %(message)s",
            level=logging.INFO,
            handlers=[
                logging.FileHandler("resource_reporter.log"),
                logging.StreamHandler(),
            ],
        )
        google_sheet = "1T3EpIZmnh3Gk-VAIGtvavTQUIpS7AluyKQ8-sJsS8vg"
        self.data_sheet = DataSheet(self.google_token, google_sheet, "Resources!A:A")
        self.fields = [
            "repo",
            "asid",
            "bibid",
            "title",
            "published",
            "create_time",
            "system_mtime",
            "created_by",
            "last_modified_by",
            "ead_location",
            "ext_number",
            "ext_portion",
            "ext_type",
            "local call no.",
            "other ctrl no. 1",
            "other ctrl no. 2",
            "other ctrl no. 3",
            "description status",
            "collecting area",
            "level",
            "scope note",
            "scopenote length",
            "bioghist note",
            "biognote length",
            "processing_priority",
            "processing_status",
        ]

    def get_as_data(self):
        self.data_sheet.clear_sheet
        spreadsheet_data = []
        spreadsheet_data.append(self.fields)
        rows_data = self.get_row_data()
        for r in rows_data:
            resource_row = self.construct_row(r)
            spreadsheet_data.append(resource_row)
        subject_count = len(spreadsheet_data) - 1
        logging.info(f"Total resource records: {subject_count}")
        self.data_sheet.append_sheet(spreadsheet_data)
        logging.info(
            f"{len(spreadsheet_data)} rows written to {self.data_sheet.spreadsheet_id}"
        )
        msg = f"{subject_count} records imported by {__file__}."
        return msg

    def construct_row(self, row_data):
        pass

    def get_row_data(self):
        """Get resource data to be written into a row.

        Yields:
            dict
        """
        # TODO: handle multiple notes of the same type (e.g., scope and content)
        # TODO: what is the utility of extent info? right now is only capturing one extent even if there are multiple; if we capture all, it may not be useful to split up number from measurement (e.g., 2 GB + 7 linear feet)
        for resource in self.as_client.all_resources():
            scope_note = self.as_client.get_specific_note_text(resource, "scopecontent")
            bio_note = self.as_client.get_specific_note_text(resource, "bioghist")
            resource_fields = {
                "repository": resource["repository"]["ref"],
                "uri": resource["uri"],
                "bibid": resource["id_0"],
                "title": resource["title"],
                "published": resource["publish"],
                "created at": resource["create_time"],
                "modified at": resource["system_mtime"],
                "created by": resource["created_by"],
                "modified by": resource["last_modified_by"],
                "finding aid location": resource.get("ead_location"),
                "local call no.": resource.get("user_defined").get("string_1"),
                "other ctrl no. 1": resource.get("user_defined").get("string_2"),
                "other ctrl no. 2": resource.get("user_defined").get("string_3"),
                "other ctrl no. 3": resource.get("user_defined").get("string_4"),
                "description status": resource.get("user_defined").get("enum_3"),
                "collecting area": resource.get("user_defined").get("enum_4"),
                "level": resource["level"],
                "scope note": scope_note[:280],
                "scopenote length": len(scope_note),
                "bioghist note": bio_note[:280],
                "biognote length": len(bio_note),
                "processing_priority": resource.get("collection_management").get(
                    "processing_priority"
                ),
                "processing_status": resource.get("collection_management").get(
                    "processing_status"
                ),
            }
            yield resource_fields
