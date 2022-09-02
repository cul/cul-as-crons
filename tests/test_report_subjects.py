import json
import unittest
from pathlib import Path
from unittest.mock import patch

from crons.report_subjects import SubjectReporter


class TestSubjectReporter(unittest.TestCase):
    @patch("crons.aspace_client.ArchivesSpaceClient.all_subjects")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__", return_value=None)
    def test_create_report(self, mock_as_init, mock_subjects):
        subject_reporter = SubjectReporter("local_settings.cfg.example")
        as_data = subject_reporter.create_report()
        self.assertTrue(as_data)

    @patch("crons.aspace_client.ArchivesSpaceClient.__init__", return_value=None)
    def test_get_row(self, mock_as_init):
        subject_reporter = SubjectReporter("local_settings.cfg.example")
        with open(Path("fixtures", "subject_record.json")) as s:
            subject = json.load(s)
        subject_row = subject_reporter.get_row(subject)
        self.assertEqual(len(subject_row), 10)
        self.assertEqual(subject_row[2], "lcsh")
