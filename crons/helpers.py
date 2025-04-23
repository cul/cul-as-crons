from datetime import datetime, timedelta

from lxml import etree


def validate_against_schema(xml, schema_name):
    """Validates XML data against ead or MARC21 schema.

    Args:
        xml (obj): xml data
        schema_name (str): ead or MARC21slim
    """
    xmlschema_doc = etree.parse(f"schemas/{schema_name}.xsd.xml")
    xmlschema = etree.XMLSchema(xmlschema_doc)
    root = etree.fromstring(xml)
    if xmlschema.validate(root):
        return True
    else:
        return False


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


def format_date(date_json):
    """Formats an ArchivesSpace data if date does not have a date expression.

    Args:
        date_json (dict): ArchivesSpace date
    """
    if date_json.get("expression"):
        date_string = date_json["expression"]
    else:
        date_string = date_json["begin"]
        if date_json.get("end"):
            date_string = f"{date_json['begin']}-{date_json['end']}"
    return date_string


def yesterday_utc():
    """Creates UTC timestamp for 24 hours ago.

    Returns:
        integer
    """
    current_time = datetime.now() - timedelta(days=1)
    return int(current_time.timestamp())
