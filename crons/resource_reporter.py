import logging

from .as_cron import BaseAsCron


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
        self.fields = [
            "repository",
            "uri",
            "bibid",
            "title",
            "published",
            "created at",
            "modified at",
            "created by",
            "modified by",
            "ead location",
            "local call no.",
            "other ctrl no. 1",
            "other ctrl no. 2",
            "other ctrl no. 3",
            "description status",
            "collecting area",
            "level",
            "extents",
            "scope note",
            "scopenote length",
            "bioghist note",
            "biognote length",
            "processing_priority",
            "processing_status",
        ]

    def get_sheet_data(self):
        spreadsheet_data = []
        spreadsheet_data.append(self.fields)
        rows_data = self.get_row_data()
        for r in rows_data:
            resource_row = self.construct_row(r)
            spreadsheet_data.append(resource_row)
        resource_count = len(spreadsheet_data) - 1
        logging.info(f"Total resource records: {resource_count}")
        self.write_data_to_sheet(
            spreadsheet_data,
            self.config["Google Sheets"]["resource_reporter_sheet"],
            self.config["Google Sheets"]["resource_reporter_range"],
        )
        msg = f"{resource_count} records imported by {__file__}."
        return msg

    def get_row_data(self):
        """Get resource data to be written into a row.

        Yields:
            dict
        """
        for resource in self.as_client.all_resources():
            scope_note = self.as_client.get_specific_note_text(resource, "scopecontent")
            bio_note = self.as_client.get_specific_note_text(resource, "bioghist")
            resource_fields = {
                "repository": resource["repository"]["ref"],
                "uri": resource["uri"],
                "bibid": resource["id_0"],
                "title": resource["title"].strip(),
                "published": resource["publish"],
                "created at": resource["create_time"],
                "modified at": resource["system_mtime"],
                "created by": resource["created_by"],
                "modified by": resource["last_modified_by"],
                "ead location": resource.get("ead_location"),
                "local call no.": resource.get("user_defined").get("string_1"),
                "other ctrl no. 1": resource.get("user_defined").get("string_2"),
                "other ctrl no. 2": resource.get("user_defined").get("string_3"),
                "other ctrl no. 3": resource.get("user_defined").get("string_4"),
                "description status": resource.get("user_defined").get("enum_3"),
                "collecting area": resource.get("user_defined").get("enum_4"),
                "level": resource["level"],
                "scope note": scope_note.strip()[:280],
                "scopenote length": len(scope_note),
                "bioghist note": bio_note.strip()[:280],
                "biognote length": len(bio_note),
                "processing_priority": resource.get("collection_management").get(
                    "processing_priority"
                )
                if resource.get("collection_management")
                else "",
                "processing_status": resource.get("collection_management").get(
                    "processing_status"
                )
                if resource.get("collection_management")
                else "",
                "extents": self.as_client.get_extents(resource),
            }
            yield resource_fields
