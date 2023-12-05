from unittest import TestCase
from unittest.mock import patch

from crons.export_data import DataExporter


class TestDataExporter(TestCase):
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__", return_value=None)
    def test_init(self, mock_aspace):
        data_exporter = DataExporter()
        self.assertTrue(data_exporter)

    def test_get_bibid(self):
        pass
