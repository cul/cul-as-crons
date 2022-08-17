import unittest
from pathlib import Path
from unittest.mock import patch

from googleapiclient.discovery import build
from googleapiclient.http import HttpMock

from crons.google_sheets_client import GoogleSheetsClient

FIXTURES_PATH = "fixtures"


def mock_build_service():
    http = HttpMock(Path(FIXTURES_PATH, "discovery.json"), {"status": "200"})
    service = build("sheets", "v4", http=http)
    return service


def mock_get_sheet_info(fixture_name):
    service = mock_build_service()
    request = service.spreadsheets().get(
        spreadsheetId="spreadsheet_it", includeGridData=False
    )
    http = HttpMock(Path(FIXTURES_PATH, fixture_name))
    response = request.execute(http=http)
    return response


class TestGoogleSheetsClient(unittest.TestCase):
    @patch("crons.google_sheets_client.build")
    def test_init(self, mock_build):
        mock_build.return_value = mock_build_service()
        google_sheets_client = GoogleSheetsClient(
            "access_token",
            "refresh_token",
            "client_id",
            "client_secret",
            "spreadsheet_id",
        )
        self.assertTrue(google_sheets_client)

    @patch("crons.google_sheets_client.GoogleSheetsClient.get_sheet_info")
    def test_get_sheet_tabs(self, mock_sheet_info):
        mock_sheet_info.return_value = mock_get_sheet_info("sheet_info.json")
        sheet_tabs = GoogleSheetsClient(
            "access_token",
            "refresh_token",
            "client_id",
            "client_secret",
            "spreadsheet_id",
        ).get_sheet_tabs()
        self.assertEqual(len(sheet_tabs), 5)
        self.assertTrue("Collection Management" in sheet_tabs)
