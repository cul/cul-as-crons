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
