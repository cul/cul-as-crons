from unittest.mock import patch

import pytest

from crons.report_subjects import SubjectReporter


@pytest.mark.usefixtures("setup_teardown_dir")
class TestSubjectReporter:

    @patch("crons.aspace_client.ArchivesSpaceClient.all_subjects")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__", return_value=None)
    def test_create_report(self, mock_as_init, mock_subjects):
        subject_reporter = SubjectReporter()
        as_data = subject_reporter.create_report()
        assert as_data
