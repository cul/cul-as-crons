# Script to harvest collection-level data from AS via OAI-PMH feed, and transform into Voyager-format MARCXML for nightly overlay.

import argparse
import datetime
import logging
import os
import subprocess
import time


class OAIHarvester(object):
    def __init__(self):
        self.destination_folder = "/cul/cul0/ldpd/archivesspace/oai/"
        logging.basicConfig(
            datefmt="%m/%d/%Y %I:%M:%S %p",
            format="%(asctime)s %(message)s",
            level=logging.INFO,
            handlers=[
                logging.FileHandler(f"{self.destination_folder}oai_harvester.log"),
                logging.StreamHandler(),
            ],
        )
        self.pyoaiharvest = os.path.join(os.path.dirname(__file__), "pyoaiharvest.py")
        self.oai_url = "https://aspace.library.columbia.edu/public/oai/"

    def run(self, today_string, harvest_all=False):
        self.today_string = today_string
        out_path_raw_all = self.harvest_all()
        if harvest_all:
            self.out_path_raw = out_path_raw_all
        else:
            self.out_path_raw = self.harvest_past_day()
        self.voyager_transform

    def harvest_all(self):
        out_path_raw_all = os.path.join(
            self.destination_folder, f"{self.today_string}.asAllRaw.xml"
        )
        self.oai_harvest(out_path_raw_all)
        return out_path_raw_all

    def harvest_past_day(self):
        out_path_raw = os.path.join(
            self.destination_folder, f"{self.today_string}.asRaw.xml"
        )
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime(
            "%Y%m%d"
        )
        self.oai_harvest(out_path_raw, from_date=yesterday)

    def voyager_transform(self):
        xslt_path = os.path.join(os.path.dirname(__file__), "../xslt/cleanOAI.xsl")
        out_path_clean = os.path.join(
            self.destination_folder, f"{self.today_string}.asClean.xml"
        )
        logging.info("Processing file with XSLT...")
        process_xml = self.saxon_process(self.out_path_raw, xslt_path, out_path_clean)
        logging.info(process_xml)

    def oai_harvest(
        self, out_path, from_date=None,
    ):
        cmd = [
            "python",
            self.pyoaiharvest,
            "-l",
            self.oai_url,
            "-m",
            "oai_marc",
            "-s",
            "collection",
            "-o",
            out_path,
        ]
        if from_date:
            cmd.append("-f")
            cmd.append(from_date)
        p = subprocess.Popen(
            [cmd],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )
        result = p.communicate()
        if result[1]:
            logging.error(result[1].decode("utf-8"))
            return f"PYOAIHARVEST ERROR: {result[1].decode('utf-8')}"
        else:
            logging.info(result[0].decode("utf-8"))
            return result[0].decode("utf-8")

    def remove_old_files(self):
        """Remove files from OAI directory that are over 30 days old."""
        old = time.time() - 30 * 24 * 60 * 60
        for f in os.listdir(self.destination_folder):
            filepath = os.path.join(self.destination_folder, f)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                if stat.st_mtime < old:
                    logging.info(f"removing: {filepath}")
                    os.remove(filepath)

    def saxon_process(
        self, saxon_path, xml_file, xslt_file, out_file=None, params=None
    ):
        cmd = [
            "java",
            "-jar",
            saxon_path,
            xml_file,
            xslt_file,
            "--suppressXsltNamespaceCheck:on",
        ]
        if out_file:
            cmd.append(f" > {out_file}")
        if params:
            cmd.insert(5, params)
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )
        result = p.communicate()
        if not result[1]:
            return result[0].decode("utf-8")
        else:
            raise Exception(result[1].decode("utf-8"))


def main():
    """Script to harvest collection-level data from AS via OAI-PMH feed and transform into Voyager-format MARCXML for nightly overlay.

    Output is (a) asRaw.xml (deltas), (b) asAllRaw.xml (all records), and (c) asClean.xml,
    transformed into Voyager MARCXML.

    Options:
    --HARVESTALL: ignore date params and get all records.
    """
    p = argparse.ArgumentParser(
        description="Script to harvest collection-level data from AS via OAI-PMH feed, and transform into Voyager-format MARCXML for nightly overlay."
    )
    p.add_argument(
        "--HARVESTALL", default=False, action="store_true", help="harvest all records?"
    )
    args = p.parse_args()
    today_string = datetime.date.today().strftime("%Y%m%d")
    OAIHarvester().run(today_string, args.HARVESTALL)


if __name__ == "__main__":
    main()
