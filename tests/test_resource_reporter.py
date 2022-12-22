import json
import types
import unittest
from pathlib import Path
from shutil import rmtree
from unittest.mock import patch

from crons.resource_reporter import ResourceReporter

TEST_DIRECTORY = "test_reports"


def mock_resources_generator():
    with open(Path("fixtures", "resource_record.json")) as s:
        resource = json.load(s)
    count = 0
    while count < 2:
        count += 1
        yield resource


SCOPE = "This collection of printed materials and photographs was assembled by Mary Alden Hopkins, a member of the Expedition, in 1952. The content primarily spans the time period just before, during, and after the expedition between the winter of 1915 and 1916. The collection centers on Hopkins' personal accounts of the expedition, biographical pamphlets, and passenger lists. Official statements issued by Louis P. Lochner, General Secretary of The Neutral Conference for Continuous Mediation, at Stockholm, are also included herein. Additionally, a letter from Lochner with the \"Appeal to Neutrals\" the Neutral Conference's manifesto, is located in this collection. Several issues of Four Lights, a magazine published by the Women's Peace Party of New York City, are included along with various newspaper clippings pertaining both to the expedition and to the war in general. The photographs in this collection are both unidentified and undated, but certainly describe the social and political activities that took place during the expedition."
BIO = 'The purpose of the Henry Ford Peace Expedition was to call a conference of delegates from non-combatant countries during World War I. In the winter of 1915-1916, the Ford Peace Expedition carried a delegation of Americans to Norway, Sweden, and Holland to meet with fellow European pacifists. Henry Ford hosted the "Peace Ship" which served as both a vehicle for travel and for collaboration amongst its passengers. During the months prior to the expedition, Hungarian feminist and pacifist Rosika Schwimmer encouraged Ford to commission the expedition. On December 4th, 1915, Henry Ford and members of the peace voyage boarded Oscar II, also known as the Peace Ship, in Hoboken, New Jersey for the expedition. The delegates for the peace expedition traveled first to Christiania (present day Oslo), Norway, and later met with fellow pacifists in Sweden and Holland. In February, 1916, members of the neutral nations from Europe met with the Ford party in Stockholm, Sweden, to form the Neutral Conference for Continuous Mediation. The expedition returned from Europe in February of 1916, but work within the Neutral Conference for Continuous Mediation continued until the end of that year. Among many active figures that influenced the expedition were Rosika Schwimmer, Ellen Key, and Louis P. Lochner.'
EXTENT = "0.42 linear feet"


class TestResourceReporter(unittest.TestCase):
    def setUp(self):
        test_path = Path(TEST_DIRECTORY)
        test_path.mkdir(exist_ok=True)

    def tearDown(self):
        rmtree(TEST_DIRECTORY)

    @patch("crons.aspace_client.ArchivesSpaceClient.all_resources")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__", return_value=None)
    def test_create_report(self, mock_as_init, mock_resources):
        resource_reporter = ResourceReporter()
        as_data = resource_reporter.create_report()
        self.assertTrue(as_data)

    @patch("crons.aspace_client.ArchivesSpaceClient.__init__")
    def test_construct_row(self, mock_as_init):
        mock_as_init.return_value = None
        resource_reporter = ResourceReporter()
        resource_data = {
            "repository": "/repositories/2",
            "uri": "/repositories/2/resources/5000",
            "bibid": "4078773",
            "title": "Henry Ford Peace Expedition Collection",
            "published": True,
            "created at": "2019-05-21T16:03:22Z",
            "modified at": "2021-11-11T20:23:31Z",
            "created by": "admin",
            "modified by": "api_user",
            "finding aid location": "http://findingaids.cul.columbia.edu/ead/nnc-rb/ldpd_4078773",
            "local call no.": "MS#0441",
            "other ctrl no. 1": "(OCoLC)495526584",
            "other ctrl no. 2": "(OCoLC)ocn495526584",
            "other ctrl no. 3": "(CStRLIN)NYCR89-A299",
            "description status": None,
            "collecting area": None,
            "level": "collection",
            "scope note": SCOPE,
            "bioghist note": BIO,
            "processing_priority": "",
            "processing_status": "",
            "extents": EXTENT,
        }
        resource_row = resource_reporter.construct_row(resource_data)
        self.assertEqual(len(resource_row), len(resource_reporter.fields))

    @patch("crons.aspace_client.ArchivesSpaceClient.get_extents", return_value=EXTENT)
    @patch(
        "crons.aspace_client.ArchivesSpaceClient.get_specific_note_text",
        side_effect=[SCOPE, BIO, SCOPE, BIO],
    )
    @patch("crons.aspace_client.ArchivesSpaceClient.all_resources")
    @patch("crons.aspace_client.ArchivesSpaceClient.__init__", return_value=None)
    def test_get_row_data(self, mock_as_init, mock_resources, mock_note, mock_extent):
        mock_resources.return_value = mock_resources_generator()
        resource_reporter = ResourceReporter()
        resource_rows = resource_reporter.get_row_data()
        self.assertIsInstance(resource_rows, types.GeneratorType)
        # print([a for a in resource_rows][0])
        self.assertEqual(len([a for a in resource_rows]), 2)
