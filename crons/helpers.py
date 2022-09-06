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
