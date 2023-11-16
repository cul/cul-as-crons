import logging
from configparser import ConfigParser
from datetime import datetime, timedelta
from pathlib import Path

from .aspace_client import ArchivesSpaceClient


class ExportData(object):
    def __init__(self):
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

    def export_resources(self, serialization="ead", timestamp=None):
        """Iterates through each repository in each ASpace instance to export data.

        Args:
            serialization (str): data export format; expects ead or marc21
            timestamp (str): utc timestamp to get records since; will calculate 24 hours ago if not provided

        """
        serialization = serialization.lower()
        timestamp = self.yesterday_utc() if None else timestamp
        for instance_name in self.config.sections():
            try:
                as_client = ArchivesSpaceClient(
                    self.config[instance_name]["baseurl"],
                    self.config[instance_name]["username"],
                    self.config[instance_name]["password"],
                )
                for repo in as_client.aspace.repositories:
                    resource_ids = as_client.aspace.client.get(
                        f"/repositories/{repo.id}/resources",
                        params={"all_ids": True, "modified_since": timestamp},
                    ).json()
                    logging.info(
                        f"Retrieving {len(resource_ids)} records from {repo.name}..."
                    )
                    for resource_id in resource_ids:
                        resource = repo.resources(resource_id)
                        if resource.publish and not resource.suppressed:
                            if self.serialization == "ead":
                                params = {
                                    "include_unpublished": False,
                                    "include_daos": True,
                                }
                                yield as_client.aspace.client.get(
                                    f"/repositories/{repo.id}/resource_descriptions/{resource_id}.xml",
                                    params=params,
                                ).content.decode("utf-8")
                            elif self.serialization == "marc21":
                                yield as_client.aspace.client.get(
                                    f"/repositories/{repo.id}/resources/marc21/{resource_id}.xml"
                                ).content.decode("utf-8")
            except Exception as e:
                logging.error(e)

    def yesterday_utc(self):
        """Creates UTC timestamp for 24 hours ago.

        Returns:
            integer
        """
        current_time = datetime.now() - timedelta(days=1)
        return int(current_time.timestamp())
