import shutil
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import HttpMock


def make_dir(directory_path, remove_first=False, parents=True):
    """Makes a directory. If remove_first is set to true, removes directory if it exists; if set to false, does not make directory if it exists"""
    path = Path(directory_path)
    if path.exists() and remove_first:
        shutil.rmtree(directory_path)
    if not path.exists():
        path.mkdir(parents=parents)


FIXTURES_PATH = "fixtures"


def make_dir(directory_path, remove_first=False, parents=True):
    """Makes a directory. If remove_first is set to true, removes directory if it exists; if set to false, does not make directory if it exists"""
    path = Path(directory_path)
    if path.exists() and remove_first:
        shutil.rmtree(directory_path)
    if not path.exists():
        path.mkdir(parents=parents)


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
