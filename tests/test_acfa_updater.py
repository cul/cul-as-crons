from unittest import TestCase
from unittest.mock import patch

from crons.acfa_updater import UpdateAllInstances, UpdateRepository


class TestUpdateAllInstances(TestCase):
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__", return_value=None)
    def test_init(self, mock_aspace):
        updated_instances = UpdateAllInstances("tmp/parent_cache")
        self.assertTrue(updated_instances)


class TestUpdateRepository(TestCase):
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__")
    def test_init(self, mock_aspace):
        updated_repositories = UpdateRepository(mock_aspace, "repo", "tmp/parent_cache")
        self.assertTrue(updated_repositories)
