import unittest
from unittest.mock import patch

from crons.as_cron import BaseAsCron


class TestBaseAsCron(unittest.TestCase):
    @patch("crons.google_sheets_client.GoogleSheetsClient.__init__")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__")
    def test_init(self, mock_aspace, mock_sheets):
        mock_aspace.return_value = None
        mock_sheets.return_value = None
        base_as_cron = BaseAsCron(
            "local_settings.cfg.example", "test_log.log", "report_subjects_sheet"
        )
        self.assertTrue(base_as_cron)
