import unittest
from unittest.mock import patch

from freezegun import freeze_time

from crons.as_cron import BaseAsCron


class TestBaseAsCron(unittest.TestCase):
    @patch("crons.google_sheets_client.GoogleSheetsClient.__init__")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__")
    def test_init(self, mock_aspace, mock_sheets):
        mock_aspace.return_value = None
        mock_sheets.return_value = None
        base_as_cron = BaseAsCron("local_settings.cfg.example", "report_subjects_sheet")
        self.assertTrue(base_as_cron)

    @freeze_time("2022-09-01 00:00:00")
    @patch("crons.google_sheets_client.DataSheet.append_sheet")
    @patch("crons.as_cron.BaseAsCron.get_as_data")
    @patch("crons.google_sheets_client.GoogleSheetsClient.__init__")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__")
    def test_run(self, mock_aspace, mock_sheets, mock_as_data, mock_append_sheet):
        msg = "500 records imported by script_name."
        mock_aspace.return_value = None
        mock_sheets.return_value = None
        mock_append_sheet.return_value = "return value"
        mock_as_data.return_value = msg
        run_cron = BaseAsCron(
            "local_settings.cfg.example", "report_subjects_sheet"
        ).run()
        self.assertEqual(
            run_cron,
            f"{msg} Start: 2022-09-01 00:00:00. Finished: 2022-09-01 00:00:00 (duration: 0:00:00)",
        )
