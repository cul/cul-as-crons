from unittest import TestCase

from freezegun import freeze_time

from crons.helpers import format_date, yesterday_utc


class TestHelpers(TestCase):
    def test_format_date(self):
        has_expression = {
            "lock_version": 0,
            "expression": "1768-1816",
            "begin": "1768",
            "end": "1816",
            "created_by": "kws2126",
            "last_modified_by": "kws2126",
            "create_time": "2022-02-04T16:40:04Z",
            "system_mtime": "2022-02-04T16:40:04Z",
            "user_mtime": "2022-02-04T16:40:04Z",
            "date_type": "inclusive",
            "label": "creation",
            "jsonmodel_type": "date",
        }
        no_expression = {
            "lock_version": 0,
            "begin": "1879",
            "end": "1927",
            "created_by": "kws2126",
            "last_modified_by": "kws2126",
            "create_time": "2022-02-04T16:40:04Z",
            "system_mtime": "2022-02-04T16:40:04Z",
            "user_mtime": "2022-02-04T16:40:04Z",
            "date_type": "inclusive",
            "label": "creation",
            "jsonmodel_type": "date",
        }
        no_expression_no_end = {
            "lock_version": 0,
            "begin": "1659",
            "created_by": "kws2126",
            "last_modified_by": "kws2126",
            "create_time": "2022-02-04T16:40:04Z",
            "system_mtime": "2022-02-04T16:40:04Z",
            "user_mtime": "2022-02-04T16:40:04Z",
            "date_type": "inclusive",
            "label": "creation",
            "jsonmodel_type": "date",
        }
        self.assertEqual(format_date(has_expression), "1768-1816")
        self.assertEqual(format_date(no_expression), "1879-1927")
        self.assertEqual(format_date(no_expression_no_end), "1659")

    @freeze_time("2023-12-01 00:00:00")
    def test_yesterday_utc(self):
        yesterday_timestamp = yesterday_utc()
        self.assertEqual(yesterday_timestamp, 1701302400)
