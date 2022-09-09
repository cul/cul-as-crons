import json
import types
import unittest
from pathlib import Path
from shutil import rmtree
from unittest.mock import patch

from crons.report_agents import AgentsReporter

TEST_DIRECTORY = "test_reports"


def mock_agents_generator():
    with open(Path("fixtures", "agent_record.json")) as s:
        agent = json.load(s)
    count = 0
    while count < 5:
        count += 1
        yield agent


class TestAgentsReporter(unittest.TestCase):
    def setUp(self):
        test_path = Path(TEST_DIRECTORY)
        test_path.mkdir(exist_ok=True)

    def tearDown(self):
        rmtree(TEST_DIRECTORY)

    @patch("crons.aspace_client.ArchivesSpaceClient.all_agents")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__")
    def test_create_report(self, mock_as_init, mock_agents):
        mock_as_init.return_value = None
        agent_reporter = AgentsReporter("local_settings.cfg.example")
        as_data = agent_reporter.create_report()
        self.assertTrue(as_data)

    @patch("crons.aspace_client.ArchivesSpaceClient.__init__")
    def test_construct_row(self, mock_as_init):
        mock_as_init.return_value = None
        agent_reporter = AgentsReporter("local_settings.cfg.example")
        agent_data = {
            "uri": "/agents/corporate_entities/1579",
            "title": "McDonnell & Sons",
            "source": "naf",
            "authority_id": "http://id.loc.gov/authorities/names/no2001020090",
            "is_linked_to_published_record": True,
            "publish": True,
            "last_modified_by": "api_user",
            "last_modified": "2021-11-12T12:33:21Z",
        }
        agent_row = agent_reporter.construct_row(agent_data)
        self.assertEqual(len(agent_row), len(agent_reporter.fields))
        self.assertIsInstance(agent_row[5], bool)

    @patch("crons.aspace_client.ArchivesSpaceClient.all_agents")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__")
    def test_get_row_data(self, mock_as_init, mock_agents):
        mock_as_init.return_value = None
        mock_agents.return_value = mock_agents_generator()
        agent_reporter = AgentsReporter("local_settings.cfg.example")
        agents_rows = agent_reporter.get_row_data()
        self.assertIsInstance(agents_rows, types.GeneratorType)
        self.assertEqual(len([a for a in agents_rows]), 5)
