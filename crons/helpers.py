from calendar import timegm
from datetime import datetime, timedelta
from re import fullmatch


class DateException(Exception):
    pass


def get_fiscal_year(accession_date):
    """Gets fiscal year (July-June) for a date.

    Args:
        accession_date (obj): datetime.date object

    Returns:
        int: fiscal year
    """
    if accession_date.year < 1700:
        return ""
    else:
        if accession_date.month > 6:
            return accession_date.year + 1
        else:
            return accession_date.year


def get_user_defined(resource, field):
    """Return user_defined data if it exists.

    Args:
        resource (dict): ASpace resource
        field (str): user defined field
    """
    if resource.get("user_defined"):
        return resource.get("user_defined").get(field)
    else:
        return ""


def formula_to_string(string):
    """Add leading single quote to strings that may be a formula in Google Sheets.

    Args:
        string: string to check for leading + or +
    """
    if string.startswith("+") or string.startswith("="):
        string = f"'{string}"
    return string


def yesterday_utc():
    """Gets UTC timestamp for 1 day ago."""
    yesterday = datetime.utcnow() - timedelta(hours=36)
    return timegm(yesterday.utctimetuple())


def empty_values(aspace_json):
    """Gets keys whose values contain only whitespace.

    Only checks values that are strings. Does not check nested objects.

    Args:
        aspace_json (dict): json representation of an ASpace object

    Returns:
        list: keys whose values contain only whitespace
    """
    only_whitespace = []
    for k, v in aspace_json.items():
        if type(v) is str:
            if str.isspace(v):
                only_whitespace.append(k)
    return only_whitespace


def leading_trailing(aspace_json):
    """Gets keys whose values contain leading or trailing whitespace.

    Args:
        aspace_json (dict): json representation of an ASpace object

    Returns:
        list: keys whose values contain leading or trailing whitespace
    """
    leading_trailing = []
    for k, v in aspace_json.items():
        if type(v) is str:
            if v.strip() != v:
                if k not in ["display_string"]:
                    leading_trailing.append(k)
    return leading_trailing


def date_is_iso(date_string):
    """Determine whether a date string conforms to ISO-8601.

    Args:
        date_string (str): date string (e.g., 1950-05-01)

    Returns:
        bool: return True if ISO date
    """
    if fullmatch(r"\d\d\d\d", date_string):
        return True
    elif fullmatch(r"\d\d\d\d-\d\d", date_string):
        return True
    else:
        try:
            datetime.fromisoformat(date_string)
            return True
        except ValueError:
            raise DateException(
                "One or more normalized dates do not conform to ISO-8601"
            )


def check_date(date):
    """Determines whether ArchivesSpace begin and end dates are ISO-8601.

    Modifies begin/end date if it contains leading or trailing whitespace.

    Args:
        date (dict): ArchivesSpace date

    Returns:
        dict: ArchivesSpace date, modified if necessary
    """
    try:
        expression = date.get("expression")
        if expression:
            if expression.strip() != expression:
                date["expression"] = expression.strip()
        begin = date.get("begin")
        if begin:
            if begin.strip() != begin:
                date["begin"] = begin.strip()
                begin = date["begin"]
            date_is_iso(begin)
        end = date.get("end")
        if end:
            if end.strip() != end:
                date["end"] = end.strip()
                end = date["end"]
            date_is_iso(end)
        return date
    except DateException as e:
        raise e
