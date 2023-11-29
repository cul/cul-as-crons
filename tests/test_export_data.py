from unittest import TestCase
from unittest.mock import patch

from freezegun import freeze_time

from crons.export_data import DataExporter


class TestDataExporter(TestCase):
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__", return_value=None)
    def test_init(self, mock_aspace):
        data_exporter = DataExporter()
        self.assertTrue(data_exporter)

    @freeze_time("2023-12-01 00:00:00")
    @patch("crons.export_data.DataExporter.__init__", return_value=None)
    def test_yesterday_utc(self, mock_init):
        yesterday_timestamp = DataExporter().yesterday_utc()
        self.assertEqual(yesterday_timestamp, 1701302400)

    def test_get_bibid(self):
        pass
