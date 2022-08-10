import unittest
from unittest.mock import patch

from freezegun import freeze_time

from crons.as_cron import BaseAsCron

MESSAGE = "500 records imported by script_name."


class TestBaseAsCron(unittest.TestCase):
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__")
    def test_init(self, mock_aspace):
        mock_aspace.return_value = None
        base_as_cron = BaseAsCron("local_settings.cfg.example", "report_subjects_sheet")
        self.assertTrue(base_as_cron)

    @freeze_time("2022-09-01 00:00:00")
    @patch("crons.as_cron.BaseAsCron.log")
    @patch("crons.as_cron.BaseAsCron.get_as_data")
    @patch("crons.as_cron.BaseAsCron.__init__")
    def test_run(self, mock_init, mock_as_data, mock_log):
        mock_init.return_value = None
        mock_as_data.return_value = MESSAGE
        run_cron = BaseAsCron(
            "local_settings.cfg.example", "report_subjects_sheet"
        ).run()
        self.assertEqual(
            run_cron,
            f"{MESSAGE} Start: 2022-09-01 00:00:00. Finished: 2022-09-01 00:00:00 (duration: 0:00:00)",
        )

    @patch("crons.google_sheets_client.DataSheet.append_sheet")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__")
    @patch("crons.google_sheets_client.DataSheet.__init__")
    def test_log(self, mock_data_sheet, mock_aspace, mock_append_sheet):
        mock_data_sheet.return_value = None
        mock_aspace.return_value = None
        mock_append_sheet.return_value = "return value"
        base_as_cron = BaseAsCron("local_settings.cfg.example", "report_subjects_sheet")
        post_log = base_as_cron.log(MESSAGE)
        self.assertTrue(post_log)
