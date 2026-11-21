from collections import defaultdict

from korpa_ingest.reader import Parsed, PriceRow


def normalize(parsed: Parsed) -> Parsed:
    """Reject conflicting duplicate identities instead of choosing a price arbitrarily."""
    groups: dict[tuple[str, str, str, str], list[PriceRow]] = defaultdict(list)
    for row in parsed.rows:
        groups[(row.format_name, row.barcode, row.kind, row.list_date.isoformat())].append(row)
    rows: list[PriceRow] = []
    for group in groups.values():
        if any(row != group[0] for row in group[1:]):
            parsed.report.error("conflicting_duplicate", count=len(group))
            parsed.report.rows_valid -= len(group)
        else:
            rows.append(group[0])
    # Monthly rows cannot overwrite a newer current product description.
    parsed.rows = sorted(rows, key=lambda row: (row.list_date, row.kind))
    return parsed
