import unittest
from unittest.mock import patch

from freezegun import freeze_time

from crons.digester import Digester


class TestDigester(unittest.TestCase):
    @patch("crons.google_sheets_client.DataSheet.__init__")
    def test_init(self, mock_sheets):
        mock_sheets.return_value = None
        digest = Digester("local_settings.cfg.example")
        self.assertTrue(digest)

    @freeze_time("2012-11-02 00:00:00")
    @patch("crons.digester.Digester.get_digest")
    @patch("crons.google_sheets_client.DataSheet.get_sheet_data")
    @patch("crons.digester.Digester.cleanup_datasheet")
    @patch("crons.google_sheets_client.DataSheet.__init__")
    def test_run(self, mock_sheets, mock_cleanup, mock_get_sheet, mock_get_digest):
        mock_sheets.return_value = None
        mock_cleanup.return_value = "0 entries removed."
        mock_get_sheet.return_value = [
            [
                "resource_reporter.py",
                "11/1/2021 2:29:54",
                "Total collection management records: 557",
            ],
            [
                "resource_reporter.py",
                "11/3/2021 2:30:03",
                "Total number of resource records: 4577",
            ],
            [
                "resource_reporter.py",
                "11/1/2021 2:30:05",
                "Script done. Updated data is available at sheet url",
            ],
        ]
        mock_get_digest.return_value = []
        Digester("local_settings.cfg.example").run()
        return True

    @freeze_time("2012-11-02 00:00:00")
    @patch("crons.google_sheets_client.DataSheet.get_sheet_data")
    @patch("crons.google_sheets_client.DataSheet.clear_sheet")
    @patch("crons.google_sheets_client.DataSheet.append_sheet")
    @patch("crons.google_sheets_client.DataSheet.__init__")
    def test_cleanup_datasheet(self, mock_sheets, mock_append, mock_clear, mock_get):
        mock_sheets.return_value = None
        mock_append.return_value = True
        mock_clear.return_value = True
        mock_get.return_value = [
            [
                "resource_reporter.py",
                "11/1/2021 2:29:54",
                "Total collection management records: 557",
            ],
            [
                "resource_reporter.py",
                "11/3/2021 2:30:03",
                "Total number of resource records: 4577",
            ],
            [
                "resource_reporter.py",
                "11/1/2021 2:30:05",
                "Script done. Updated data is available at sheet url",
            ],
        ]
        cleaned_digest = Digester("local_settings.cfg.example").cleanup_datasheet()
        self.assertTrue(cleaned_digest)

    @freeze_time("2012-11-02 00:00:00")
    @patch("crons.google_sheets_client.DataSheet.get_sheet_data")
    @patch("crons.google_sheets_client.DataSheet.__init__")
    def test_get_digest(self, mock_sheets, mock_get):
        mock_sheets.return_value = None
        mock_get.return_value = [
            [
                "resource_reporter.py",
                "11/1/2021 2:29:54",
                "Total collection management records: 557",
            ],
            [
                "resource_reporter.py",
                "11/1/2021 2:30:03",
                "Total number of resource records: 4577",
            ],
            [
                "resource_reporter.py",
                "11/1/2021 2:30:05",
                "Script done. Updated data is available at sheet url",
            ],
        ]
        digest = Digester("local_settings.cfg.example").get_digest()
        self.assertTrue(digest)

    @patch("crons.google_sheets_client.DataSheet.append_sheet")
    @patch("crons.google_sheets_client.DataSheet.__init__")
    def test_post_digest(self, mock_sheets, mock_append):
        mock_sheets.return_value = None
        mock_append.return_value = True
        log_message = "message to log"
        posted_digest = Digester("local_settings.cfg.example").post_digest(
            "scrpt name", log_message
        )
        self.assertTrue(posted_digest)
