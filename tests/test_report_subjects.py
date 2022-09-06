import unittest
from unittest.mock import patch

from crons.report_subjects import SubjectReporter


class TestSubjectReporter(unittest.TestCase):
    @patch("crons.aspace_client.ArchivesSpaceClient.all_subjects")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__", return_value=None)
    def test_create_report(self, mock_as_init, mock_subjects):
        subject_reporter = SubjectReporter("local_settings.cfg.example")
        as_data = subject_reporter.create_report()
        self.assertTrue(as_data)
