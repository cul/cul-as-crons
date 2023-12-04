import argparse
from pathlib import Path

from crons.export_data import DataExporter


def main():
    parser = argparse.ArgumentParser(
        description="Exports EAD files from all ASpace instances in config file to a directory and deletes related HTML files"
    )
    parser.add_argument("parent_cache", help="Parent directory of EAD and HTML caches")
    args = parser.parse_args()
    ead_cache = Path(args.parent_cache, "ead_cache")
    html_cache = Path(args.parent_cache, "html_cache")
    data_exporter = DataExporter()
    bibids = []
    for bibid, ead in data_exporter.export_resources(serialization="ead"):
        if bibid.isnumeric():
            ead_filepath = Path(ead_cache, f"as_ead_ldpd_{bibid}.xml")
        else:
            ead_filepath = Path(ead_cache, f"as_ead_{bibid}.xml")
        with open(ead_filepath, "w") as ead_file:
            ead_file.write(ead)
        for matching_file in html_cache.glob(f"*{bibid}*"):
            if matching_file.suffix == ".html":
                matching_file.unlink()
        bibids.append(bibid)
        # TODO: trigger reindex


if __name__ == "__main__":
    main()
