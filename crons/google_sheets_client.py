# TODO: replace oauth2client (deprecated) with google-auth

import csv
import uuid

import googleapiclient
import oauth2client
from httplib2 import Http


class GoogleSheetsClient(object):
    def __init__(self, token, spreadsheet_id):
        """Sets up client to work with a spreadsheet using the Google Sheets API.

        Args:
            token (str): path to token JSON file
            spreadsheet_id (str): the spreadsheet to request
        """
        credentials = oauth2client.file.Storage(token).get()
        self.service = googleapiclient.discovery.build(
            "sheets", "v4", http=credentials.authorize(Http())
        )
        self.spreadsheet_id = spreadsheet_id

    def get_sheet_info(self):
        """Return data about a spreadsheet."""
        request = self.service.spreadsheets().get(
            spreadsheetId=self.spreadsheet_id, includeGridData=False
        )
        response = request.execute()
        return response

    def get_sheet_tabs(self):
        """Return a list of tab names for a given sheet."""
        sheet_data = self.get_sheet_info()
        sheet_tabs = [s["properties"]["title"] for s in sheet_data["sheets"]]
        return sheet_tabs


class DataSheet(GoogleSheetsClient):
    def __init__(self, token, spreadsheet_id, data_range):
        """Work with a range in a spreadsheet using Google Sheets API.

        Args:
            token (str): path to token JSON file
            spreadsheet_id (str): the spreadsheet to request
            data_range (str): the A1 notation of a range to search for a logical table of data
        """
        super(DataSheet, self).__init__(token, spreadsheet_id)
        self.data_range = data_range

    def get_sheet_data(self):
        """Return sheet data as list of rows."""
        request = (
            self.service.spreadsheets()
            .values()
            .get(
                spreadsheetId=self.spreadsheet_id,
                range=self.data_range,
                valueRenderOption="FORMATTED_VALUE",
                dateTimeRenderOption="SERIAL_NUMBER",
            )
        )
        the_data = request.execute()
        response = the_data["values"] if "values" in the_data else []
        return response

    def get_sheet_data_columns(self):
        """Return sheet data in columns instead of rows."""
        request = (
            self.service.spreadsheets()
            .values()
            .get(
                spreadsheetId=self.spreadsheet_id,
                range=self.data_range,
                valueRenderOption="FORMATTED_VALUE",
                majorDimension="COLUMNS",
                dateTimeRenderOption="SERIAL_NUMBER",
            )
        )
        the_data = request.execute()
        response = the_data["values"] if "values" in the_data else []
        return response

    def get_sheet_data_series(self):
        """Get data columns as a dict with key and series.

        Note that series keys must be unique; if column heads are duplicated a UUID will be appended to key in output.
        """
        the_cols = self.get_sheet_data_columns()
        the_series = {}
        for col in [x for x in the_cols if len(x) > 0]:
            key = col.pop(0)
            if key in the_series:
                key_new = "{}_{}".format(key, uuid.uuid1())
                print(f"Warning: Duplicate column heading {key}. Renaming as {key_new}")
                the_series[key_new] = col
            else:
                the_series[key] = col
        return the_series

    def get_sheet_url(self):
        """Pull the title of tab from the range."""
        tab_name = self.data_range.split("!")[0]
        sheet_info = self.get_sheet_info()["sheets"]
        # Look for sheet matching name and get its ID
        sheet_id = next(
            i["properties"]["sheetId"]
            for i in sheet_info
            if i["properties"]["title"] == tab_name
        )
        the_url = f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}/edit#gid={sheet_id}"
        return the_url

    def clear_sheet(self):
        clear_values_request_body = {
            # TODO: Add desired entries to the request body.
        }
        request = (
            self.service.spreadsheets()
            .values()
            .clear(
                spreadsheetId=self.spreadsheet_id,
                range=self.data_range,
                body=clear_values_request_body,
            )
        )
        response = request.execute()
        return response

    def append_sheet(self, data):
        """Append rows to end of detected table.

        Note: the range is only used to identify a table; values will be appended at the end of table, not at end of range.
        https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/append
        https://developers.google.com/sheets/api/reference/rest/v4/ValueInputOption
        https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/append#InsertDataOption
        """
        request = (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=self.data_range,
                valueInputOption="USER_ENTERED",
                insertDataOption="OVERWRITE",
                body={"values": data},
            )
        )
        response = request.execute()
        return response

    def sheet_lookup(self, search_str, target_col, return_cols):
        """Provide string to match, the column to match in, and col(s) to return.

        The return_col can either be an integer or a list of integers, e.g.,
        target_col=0, return_col=[1,2], which will return an array of results. Will
        return multiple matches in a list.

        Args:
            search_str (str):
            target_col (int): index of column to match in
            return_cols (int or list): column(s) to return. Can be either an integer or a list of integers.

        Returns:
            list: list of results

        """
        sheet_data = self.get_sheet_data()
        results = []
        if not isinstance(return_cols, list):
            return_cols = [return_cols]
        for row in [x for x in sheet_data if x[target_col] == search_str]:
            result_set = [row[col] for col in return_cols]
            results.append(result_set)
        return results

    def import_csv(self, a_csv, delim=",", quote="NONE"):
        """Will clear contents of sheet range first.

        Args:
            a_csv (str): csv to import
            delim (str): comma by default, can be pipe, colon, etc.
            quote (str): Can be: ALL, MINIMAL, NONNUMERIC, NONE
        """
        self.clear_sheet()
        quote_behavior = {
            "ALL": csv.QUOTE_ALL,
            "MINIMAL": csv.QUOTE_MINIMAL,
            "NONNUMERIC": csv.QUOTE_NONNUMERIC,
            "NONE": csv.QUOTE_NONE,
        }
        quote_param = quote_behavior.get(quote.upper())
        # TODO: Improve ability to pass parameters through to csv dialect options. See https://docs.python.org/3/library/csv.html
        csv.register_dialect("my_dialect", delimiter=delim, quoting=quote_param)
        data = []
        with open(a_csv) as the_csv_data:
            for row in csv.reader(the_csv_data, "my_dialect"):
                data.append(row)
        request = (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=self.data_range,
                valueInputOption="USER_ENTERED",
                insertDataOption="OVERWRITE",
                body={"values": data},
            )
        )
        response = request.execute()
        return response