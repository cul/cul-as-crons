import email
import logging
import smtplib
import time
from configparser import ConfigParser
from pathlib import Path

import requests

from .aspace_client import ArchivesSpaceClient
from .helpers import validate_against_schema, yesterday_utc


class UpdateAllInstances(object):
    def __init__(self, parent_cache):
        """If no date is provided, default to 24 hours ago.

        Expects a config file with (only) an unlimited number of repositories in the following format:

        [Instance_Name]
        baseurl: https://sandbox.archivesspace.org/api/
        username: admin
        password: admin
        """
        current_path = Path(__file__).parents[1].resolve()
        log_file = Path(current_path, "acfa_updater.log")
        logging.basicConfig(
            datefmt="%m/%d/%Y %I:%M:%S %p",
            format="%(asctime)s %(message)s",
            level=logging.INFO,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(),
            ],
        )
        config_file = Path(current_path, "as_export.cfg")
        self.config = ConfigParser()
        self.config.read(config_file)
        self.parent_cache = parent_cache

    def all_repos(self, acfa_api_token):
        """Iterates through each repository in each ASpace instance."""
        for instance_name in self.config.sections():
            errors = []
            as_client = ArchivesSpaceClient(
                self.config[instance_name]["baseurl"],
                self.config[instance_name]["username"],
                self.config[instance_name]["password"],
            )
            email_from = self.config[instance_name]["email_from"]
            email_to = self.config[instance_name]["email_to"]
            email_server = self.config[instance_name]["email_server"]
            for repo in as_client.aspace.repositories:
                if repo.publish:
                    repo_errors = UpdateRepository(
                        acfa_api_token, as_client, repo, self.parent_cache
                    ).daily_update()
                    errors.extend(repo_errors)
            if errors:
                self.send_error_email(email_from, email_to, email_server, errors)

    def send_error_email(self, email_from, email_to, email_server, errors):
        message = email.message.EmailMessage()
        message["From"] = email_from
        message["To"] = email_to
        message["Subject"] = "Finding Aid Export Error(s)"
        body = "The following errors occurred during the nightly finding aid update process:\n\n"
        for error in errors:
            body += f"{error}\n"
        message.set_content(body)
        server = smtplib.SMTP(email_server)
        server.send_message(message)
        server.quit()


class UpdateRepository(object):
    def __init__(self, acfa_api_token, as_client, repo, parent_cache):
        self.export_params = {
            "include_unpublished": False,
            "include_daos": True,
        }
        self.acfa_base_url = "https://findingaids.library.columbia.edu/"
        self.acfa_api_token = acfa_api_token
        self.as_client = as_client
        self.repo = repo
        self.ead_cache = Path(parent_cache, "ead_cache")
        self.pdf_cache = Path(parent_cache, "pdf_cache")

    def daily_update(self, timestamp=None):
        """Updates EAD and HTML caches, updates index."""
        bibids = []
        timestamp = yesterday_utc() if timestamp is None else timestamp
        errors = []
        for resource in self.updated_resources(timestamp):
            ead_response = self.as_client.aspace.client.get(
                f"/repositories/{self.repo.id}/resource_descriptions/{resource.id}.xml",
                params=self.export_params,
            )
            if getattr(resource, "id_2", False):
                bibid = f"{resource.id_0}-{getattr(resource, 'id_1', '')-{getattr(resource, 'id_2')}}"
            elif getattr(resource, "id_1", False):
                bibid = f"{resource.id_0}-{getattr(resource, 'id_1')}"
            else:
                bibid = f"{resource.id_0}"
            try:
                if not validate_against_schema(ead_response.content, "ead"):
                    logging.info(f"{bibid}: Invalid EAD")
                    errors.append(f"Invalid EAD: {bibid}")
                if bibid.isnumeric():
                    bibid = f"cul-{bibid}"
                ead_filepath = Path(self.ead_cache, f"as_ead_{bibid}.xml")
                with open(ead_filepath, "w") as ead_file:
                    ead_file.write(ead_response.content.decode("utf-8"))
                if bibid != "10815449" or bibid != "cul-10815449":
                    pdf_filepath = Path(self.pdf_cache, f"as_ead_{bibid}.pdf")
                    pdf_response = self.create_pdf_job(resource.id)
                    with open(pdf_filepath, "wb") as pdf_file:
                        pdf_file.write(pdf_response.content)
                bibids.append(bibid)
            except Exception as e:
                logging.error(f"{bibid}: {e}")
                errors.append(f"Error when processing {bibid}: {e}")
        self.update_index(bibids)
        return errors

    def create_pdf_job(self, resource_id):
        data = {
            "jsonmodel_type": "job",
            "status": "queued",
            "has_modified_records": False,
            "inactive_record": False,
            "job": {
                "jsonmodel_type": "print_to_pdf_job",
                "source": f"/repositories/{self.repo.id}/resources/{resource_id}",
                "include_unpublished": False,
            },
        }
        response = self.as_client.aspace.client.post(
            f"repositories/{self.repo.id}/jobs", json=data
        )
        response.raise_for_status()
        job_uri = response.json().get("uri")
        job_json = self.as_client.aspace.client.get(job_uri).json()
        start_time = time.time()
        max_minutes = 15
        while True:
            job_json = self.as_client.aspace.client.get(job_uri).json()
            if time.time() - start_time >= max_minutes * 60:
                raise Exception(f"Job timed out after {max_minutes} minutes")
            elif job_json["status"] == "completed":
                output_file_id = self.as_client.aspace.client.get(
                    f"{job_uri}/output_files"
                ).json()[0]
                pdf_response = self.as_client.aspace.client.get(
                    f"{job_uri}/output_files/{output_file_id}"
                )
                return pdf_response
            elif job_json["status"] == "failed":
                raise Exception("PDF export failed!")
            else:
                time.sleep(1)

    def index_only(self, timestamp=None):
        """Only update index for recently updated resources."""
        bibids = []
        timestamp = yesterday_utc() if timestamp is None else timestamp
        for resource in self.updated_resources(timestamp):
            bibid = f"{resource.id_0}{getattr(resource, 'id_1', '')}"
            try:
                if bibid.isnumeric():
                    bibid = f"cul-{bibid}"
                bibids.append(bibid)
            except Exception as e:
                print(bibid, e)
        print(bibids)
        response = self.update_index(bibids)
        print(response.content)

    def updated_resources(self, timestamp):
        resource_ids = self.as_client.aspace.client.get(
            f"/repositories/{self.repo.id}/resources",
            params={"all_ids": True, "modified_since": timestamp},
        ).json()
        for resource_id in resource_ids:
            resource = self.repo.resources(resource_id)
            if resource.publish and not resource.suppressed:
                yield resource

    def update_index(self, bibids):
        url = f"{self.acfa_base_url}api/v1/index/index_ead"
        json_data = {"bibids": bibids}
        headers = {
            "Authorization": f"Token {self.acfa_api_token}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, json=json_data, headers=headers)
        return response
