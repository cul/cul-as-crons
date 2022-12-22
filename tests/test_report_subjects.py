import unittest
from pathlib import Path
from shutil import rmtree
from unittest.mock import patch

from crons.report_subjects import SubjectReporter

TEST_DIRECTORY = "test_reports"


class TestSubjectReporter(unittest.TestCase):
    def setUp(self):
        test_path = Path(TEST_DIRECTORY)
        test_path.mkdir(exist_ok=True)

    def tearDown(self):
        rmtree(TEST_DIRECTORY)

    @patch("crons.aspace_client.ArchivesSpaceClient.all_subjects")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__", return_value=None)
    def test_create_report(self, mock_as_init, mock_subjects):
        subject_reporter = SubjectReporter()
        as_data = subject_reporter.create_report()
        self.assertTrue(as_data)
