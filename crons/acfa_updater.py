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
        config_file = Path(current_path, "as_export.cfg")
        self.config = ConfigParser()
        self.config.read(config_file)
        self.parent_cache = parent_cache

    def all_repos(self, acfa_api_token):
        """Iterates through each repository in each ASpace instance."""
        for instance_name in self.config.sections():
            as_client = ArchivesSpaceClient(
                self.config[instance_name]["baseurl"],
                self.config[instance_name]["username"],
                self.config[instance_name]["password"],
            )
            for repo in as_client.aspace.repositories:
                print(f"Updating {repo.name}")
                UpdateRepository(
                    acfa_api_token, as_client, repo, self.parent_cache
                ).daily_update()

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
        for resource in self.updated_resources(timestamp):
            ead_response = self.as_client.aspace.client.get(
                f"/repositories/{self.repo.id}/resource_descriptions/{resource.id}.xml",
                params=self.export_params,
            )
            bibid = f"{resource.id_0}{getattr(resource, 'id_1', '')}"
            try:
                if not validate_against_schema(ead_response.content, "ead"):
                    print(f"{bibid}: Invalid EAD")
                    # TODO: email?
                if bibid.isnumeric():
                    bibid = f"ldpd_{bibid}"
                ead_filepath = Path(self.ead_cache, f"as_ead_{bibid}.xml")
                with open(ead_filepath, "w") as ead_file:
                    ead_file.write(ead_response.content.decode("utf-8"))
                bibids.append(bibid)
            except Exception as e:
                print(bibid, e)
                # TODO: email?
        self.update_index(bibids)

    def index_only(self, timestamp=None):
        """Only update index for recently updated resources."""
        bibids = []
        timestamp = yesterday_utc() if timestamp is None else timestamp
        for resource in self.updated_resources(timestamp):
            bibid = f"{resource.id_0}{getattr(resource, 'id_1', '')}"
            try:
                if bibid.isnumeric():
                    bibid = f"ldpd_{bibid}"
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
        
    def save_pdf(self, resource):
        try:
            pdf_response = self.as_client.aspace.client.get(
                f"/repositories/{self.repo.id}/resource_descriptions/{resource.id}.pdf",
                params=self.export_params,
            )
        except Exception as e:
            pass

