import json
import types
import unittest
from pathlib import Path
from shutil import rmtree
from unittest.mock import patch

from freezegun import freeze_time

from crons.report_accessions import AccessionsReporter

TEST_DIRECTORY = "test_reports"


def mock_accessions_generator(repo):
    with open(Path("fixtures", f"{repo}_accession.json")) as s:
        accession = json.load(s)
    count = 0
    while count < 2:
        count += 1
        yield accession


class TestAccessionsReporter(unittest.TestCase):
    def setUp(self):
        test_path = Path(TEST_DIRECTORY)
        test_path.mkdir(exist_ok=True)

    def tearDown(self):
        rmtree(TEST_DIRECTORY)

    @patch("crons.aspace_client.ArchivesSpaceClient.get_json_response")
    @patch("crons.aspace_client.ArchivesSpaceClient.accessions_from_repository")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__", return_value=None)
    def test_construct_sheet(
        self, mock_as_init, mock_accessions, mock_get_json_response
    ):
        mock_accessions.return_value = mock_accessions_generator("rbml")
        with open(Path("fixtures", "rbml_resource.json")) as s:
            resource = json.load(s)
        mock_get_json_response.return_value = resource
        accession_reporter = AccessionsReporter()
        constructed_sheet = accession_reporter.construct_sheet("rbml", 2)
        self.assertTrue(constructed_sheet)

    @patch("crons.aspace_client.ArchivesSpaceClient.__init__", return_value=None)
    def test_construct_row(self, mock_as_init):
        accession_reporter = AccessionsReporter()
        accession_data = {
            "repository": "/repositories/3",
            "uri": "/repositories/3/accessions/4599",
            "title": "GSAPP",
            "accession_date": "1999-01-01",
            "id_0": "1999.017",
            "id_1": None,
            "id_2": None,
            "id_3": None,
            "integer_1": None,
            "created at": "2018-10-15T15:02:19Z",
            "modified at": "2021-11-12T12:33:11Z",
            "created by": "sh2309",
            "modified by": "sh2309",
            "resource_bibid": "6636103",
            "resource_asid": "/repositories/3/resources/761",
            "year": 1999,
            "fiscal_year": 1999,
            "processing_status": "completed",
            "processing_priority": None,
            "recent": False,
            "extents": "",
        }
        accession_row = accession_reporter.construct_row(accession_data)
        self.assertEqual(len(accession_row), len(accession_reporter.fields))

    @freeze_time("2021-11-02 00:00:00")
    @patch("crons.aspace_client.ArchivesSpaceClient.get_json_response")
    @patch("crons.aspace_client.ArchivesSpaceClient.accessions_from_repository")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__", return_value=None)
    def test_get_row_data(self, mock_as_init, mock_accessions, mock_get_json_response):
        repositories = {"rbml": 2, "avery": 3, "rbmlbooks": 6}
        for repo, repo_id in repositories.items():
            mock_accessions.return_value = mock_accessions_generator(repo)
            with open(Path("fixtures", f"{repo}_resource.json")) as s:
                resource = json.load(s)
            mock_get_json_response.return_value = resource
            accession_reporter = AccessionsReporter()
            accession_rows = accession_reporter.get_row_data(repo_id)
            self.assertTrue(accession_rows)
            self.assertIsInstance(accession_rows, types.GeneratorType)
            self.assertEqual(len([a for a in accession_rows]), 2)
