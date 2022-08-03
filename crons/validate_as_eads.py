import logging
import os
import re
import subprocess
from configparser import ConfigParser
from datetime import datetime

import digester  # for generating composite digest of report info.
from cul_archives_utils import xml_utils

from .google_sheets_client import DataSheet


class ParseException(Exception):
    pass


class EadValidator(object):
    """Copy the latest EAD files and parse, validate them against schema, and evaluate them with XSLT audit stylesheet.

    Output is piped to a google sheet report using sheetFeeder.
    """

    def __init__(self, config_file):
        self.config = ConfigParser()
        self.config.read(config_file)
        logging.basicConfig(
            datefmt="%m/%d/%Y %I:%M:%S %p",
            format="%(asctime)s %(message)s",
            level=logging.INFO,
            handlers=[
                logging.FileHandler("subject_reporter.log"),
                logging.StreamHandler(),
            ],
        )
        self.script_name = os.path.basename(__file__)
        self.my_path = os.path.basename(__file__)
        google_token = self.config["Google Sheets"]["token"]
        self.sheet_id = "1Ltf5_hhR-xN4YSvNWmPX8bqJA1UjqAaSjgeHBr_5chA"
        self.parse_sheet = DataSheet(google_token, self.sheet_id, "parse!A:Z")
        self.validation_sheet = DataSheet(google_token, self.sheet_id, "schema!A:Z")
        self.eval_sheet = DataSheet(google_token, self.sheet_id, "eval!A:Z")
        self.log_sheet = DataSheet(google_token, self.sheet_id, "log!A:Z")
        self.fa_app_cache = "ldpdserv@ldpd-nginx-prod1:/opt/passenger/ldpd/findingaids_prod/caches/ead_cache"
        self.ead_cache = "/cul/cul0/ldpd/archivesspace/ead_cache"
        self.dest_path = "/cul/cul0/ldpd/archivesspace/"
        self.ssh_key_path = self.config["FILES"]["keyPath"]
        self.schema_path = "/opt/dcps/dcps-utils/archivesspace/schemas/cul_as_ead.rng"
        self.jing_utils = xml_utils.JingUtils(
            self.config["FILES"]["jingPath"],
            self.schema_path,
        )
        self.saxon_path = self.config["FILES"]["saxonPath"]
        self.xslt_path = "/opt/dcps/dcps-utils/archivesspace/schemas/cul_as_ead.xsl"
        self.csv_out_path = "/opt/dcps/dcps-utils/archivesspace/as_crons/temp_out.txt"

    def run(self):
        # TODO: handle google API response time error
        start_time = datetime.now()
        try:
            logging.info("====== Syncing files from production cache... ======\n")
            logging.info(self.sync_files())
            logging.info("====== Checking well-formedness of XML... ======\n")
            logging.info(self.check_xml)
            logging.info("====== Validating files against RNG schema... ======\n")
            self.validate_with_jing()
            logging.info("====== Evaluating with XSLT ... ======\n")
            logging.info(self.evaluate_with_saxon())
            end_time = datetime.now()
            msg = f"EADs from {self.ead_cache} evaluated by {self.schema_path} and {self.xslt_path}. Start: {start_time}. Finished: {end_time} (duration: {end_time - start_time})."
            self.log_sheet.append_data([msg])
            self.log_to_digest()
            logging.info(
                f"Script done. Check report sheet for more details: {self.validation_sheet.get_sheet_url()}"
            )
        except ParseException as p:
            logging.error(f"Error parsing XML: {p}")

    def sync_files(self):
        cmd = [
            "/usr/bin/rsync",
            "-zarvhe",
            f'"ssh -i {self.ssh_key_path}"',
            "--exclude",
            "clio*",
            "--exclude",
            "*.txt",
            self.fa_app_cache,
            self.dest_path,
        ]
        rsync = subprocess.run(cmd, capture_output=True, check=True)
        return rsync.stdout.decode("utf-8")

    def check_xml(self):
        cmd = ["xmllint", self.ead_cache, "/*", "--noout"]
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            raise ParseException(e)

    def validate_with_jing(self):
        x = self.jing_utils.jing_process_batch(self.ead_cache, "as_ead*")
        pattern = re.compile(r"^.*?as_ead_ldpd_(\d+)\.xml:(.*)$")
        schema_errors = []
        for line in str(x).splitlines():
            if "as_ead" in line:
                err_msg = pattern.search(line)
                if err_msg:
                    schema_errors.append((err_msg.group(1), err_msg.group(2)))
        if schema_errors:
            for err in [f"{p[0]}: {p[1]}" for p in schema_errors if len(p) > 1]:
                logging.error(f"VALIDATION ERROR: {err}")
            self.validation_sheet.clear_sheet()
            self.validation_sheet.append_sheet(schema_errors)
            self.schema_err_cnt = len(schema_errors)
        else:
            logging.info("All files are valid")
            self.schema_err_cnt = 0

    def evaluate_with_saxon(self):
        cmd = [
            "java",
            "-jar",
            self.saxon_path,
            self.xslt_path,
            self.xslt_path,
            f"filePath={self.ead_cache}",
            "--suppressXsltNamespaceCheck:on",
            ">",
            self.csv_out_path,
        ]
        subprocess.run(cmd, check=True)
        self.eval_sheet.clear_sheet()
        self.eval_sheet.import_csv(self.csv_out_path, delim="|")
        evals = self.eval_sheet.get_sheet_data_columns()[0]
        eval_bibs = set(evals)
        self.warnings_cnt = len(eval_bibs)
        if evals:
            msg = f"{len(evals)} warnings in {self.warnings_cnt} files."
        else:
            msg = "There were no problems found!"
        return msg

    def log_to_digest(self):
        for msg in [
            f"Files with schema errors: {self.schema_err_cnt}",
            f"Files with warnings: {self.warnings_cnt}",
        ]:
            digester.post_digest(self.script_name, msg)
