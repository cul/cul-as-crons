import json
import unittest
from pathlib import Path
from unittest.mock import patch

from crons.report_subjects import SubjectReporter

FIELDS = [
    ("uri", "uri"),
    ("title", "title"),
    ("source", "source"),
    ("authority_id", "authority_id"),
    ("is_linked_to_published_record", "is_linked_to_published_record"),
    ("publish", "publish"),
    ("last_modified_by", "last_modified_by"),
    ("last_modified", "system_mtime"),
]


class TestSubjectReporter(unittest.TestCase):
    @patch("crons.aspace_client.ArchivesSpaceClient.all_subjects")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__", return_value=None)
    def test_create_report(self, mock_as_init, mock_subjects):
        subject_reporter = SubjectReporter("local_settings.cfg.example")
        subject_reporter.fields = FIELDS
        as_data = subject_reporter.create_report()
        self.assertTrue(as_data)

    @patch("crons.report_subjects.SubjectReporter.__init__", return_value=None)
    def test_get_row(self, mock_init):
        subject_reporter = SubjectReporter("local_settings.cfg.example")
        subject_reporter.fields = FIELDS
        with open(Path("fixtures", "subject_record.json")) as s:
            subject = json.load(s)
        subject_row = subject_reporter.get_row(subject)
        self.assertEqual(len(subject_row), 10)
        self.assertEqual(subject_row[2], "lcsh")
