import email
import logging
import smtplib
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
        self.errors = []

    def daily_update(self, timestamp=None):
        """Updates EAD and PDF caches, updates index."""
        fa_ids = []
        timestamp = yesterday_utc() if timestamp is None else timestamp
        for resource in self.as_client.updated_resources(timestamp):
            fa_id = self.get_fa_id(resource)
            try:
                self.save_ead(resource, fa_id)
                # skip Prokofiev
                if fa_id == "cul-10815449":
                    self.save_pdf(resource, fa_id)
                fa_ids.append(fa_id)
            except Exception as e:
                logging.error(f"{fa_id}: {e}")
                self.errors.append(
                    f"Error when processing {fa_id} ({self.repo.repo_code}): {e}"
                )
        self.update_index(fa_ids)
        return self.errors

    def save_pdf(self, resource, fa_id):
        pdf_filepath = Path(self.pdf_cache, f"as_ead_{fa_id}.pdf")
        pdf_response = self.as_client.create_pdf_job(resource.id)
        with open(pdf_filepath, "wb") as pdf_file:
            pdf_file.write(pdf_response.content)

    def save_ead(self, resource, fa_id):
        ead_response = self.as_client.aspace.client.get(
            f"/repositories/{self.repo.id}/resource_descriptions/{resource.id}.xml",
            params=self.export_params,
        )
        if not validate_against_schema(ead_response.content, "ead"):
            logging.info(f"{fa_id}: Invalid EAD")
            self.errors.append(f"Invalid EAD: {fa_id}")
        ead_filepath = Path(self.ead_cache, f"as_ead_{fa_id}.xml")
        with open(ead_filepath, "w") as ead_file:
            ead_file.write(ead_response.content.decode("utf-8"))

    def get_fa_id(self, resource):
        if getattr(resource, "id_2", False):
            fa_id = f"{resource.id_0}-{getattr(resource, 'id_1', '')}-{getattr(resource, 'id_2')}"
        elif getattr(resource, "id_1", False):
            fa_id = f"{resource.id_0}-{getattr(resource, 'id_1')}"
        else:
            id_0 = str(resource.id_0).strip()
            if id_0.isnumeric() or id_0.startswith("in"):
                fa_id = f"cul-{id_0}"
            else:
                fa_id = id_0
        return fa_id

    def index_only(self, timestamp=None):
        """Only update index for recently updated resources."""
        fa_ids = []
        timestamp = yesterday_utc() if timestamp is None else timestamp
        for resource in self.as_client.updated_resources(timestamp):
            fa_id = self.get_fa_id(resource)
            fa_ids.append(fa_id)
        print(fa_ids)
        response = self.update_index(fa_ids)
        print(response.content)

    def update_index(self, fa_ids):
        url = f"{self.acfa_base_url}api/v1/index/index_ead"
        json_data = {"bibids": fa_ids}
        headers = {
            "Authorization": f"Token {self.acfa_api_token}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, json=json_data, headers=headers)
        try:
            response.raise_for_status()
            if response.json()["failure"] > 0:
                errors_msgs = "; ".join(response.json()["errorMessages"])
                self.errors.append(
                    f"Failed to index {response.json()['failure']} collections: {errors_msgs}"
                )
        except requests.exceptions.HTTPError as e:
            error_msg = f"Error indexing {', '.join(fa_ids)}: {e}"
            self.errors.append(error_msg)
            logging.error(error_msg)
        return response
