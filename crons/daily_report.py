import email
import logging
import smtplib
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path

from .aspace_client import ArchivesSpaceClient
from .helpers import yesterday_utc


class DailyReport(object):
    """Generates and sends a daily report of updated ArchivesSpace resource records."""

    def __init__(self):
        """Initializes the DailyReport class.

        Sets up logging, reads configuration from 'as_export.cfg', and
        initializes the ArchivesSpaceClient with credentials from the config.
        Also retrieves email sender, recipient, and server details.
        """
        current_path = Path(__file__).parents[1].resolve()
        log_file = Path(current_path, "daily_report.log")
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
        self.as_client = ArchivesSpaceClient(
            self.config["CUL"]["baseurl"],
            self.config["CUL"]["username"],
            self.config["CUL"]["password"],
        )
        self.email_from = self.config["CUL"]["email_from"]
        self.email_to = self.config["CUL"]["email_to"]
        self.email_server = self.config["CUL"]["email_server"]

    def run(self):
        """Executes the daily report generation and sending process.

        Fetches updated resource records from ArchivesSpace for each published
        repository since 24 hours ago, constructs an email body with the report,
        and then sends the email.
        """
        try:
            timestamp = yesterday_utc()
            record_count = 0
            email_body = f"The following records have been updated since {datetime.fromtimestamp(timestamp).isoformat()}:\n\n"
            for repo in self.as_client.aspace.repositories:
                if repo.publish:
                    repository = Repository(self.as_client, repo, timestamp)
                    repository.get_report()
                    record_count += len(repository.published_resources)
                    record_count += len(repository.unpublished_resources)
                    email_body += repository.email_message
            self.send_report_email(record_count, email_body)
        except Exception as e:
            logging.error(e)

    def send_report_email(self, record_count, email_body):
        """Sends the daily report email.

        Args:
            record_count (int): The total number of updated resource records.
            email_body (str): The body content of the email.
        """
        try:
            message = email.message.EmailMessage()
            message["From"] = self.email_from
            message["To"] = self.email_to
            message["Subject"] = f"{record_count} Resource Records Updated"
            message.set_content(email_body)
            server = smtplib.SMTP(self.email_server)
            server.send_message(message)
            server.quit()
        except Exception:
            raise


class Repository(object):
    """Represents an ArchivesSpace repository and handles its daily reporting.

    This class is responsible for fetching updated resources within a specific
    repository and constructing the part of the email body related to it.
    """

    def __init__(self, as_client, repo, timestamp):
        """Initializes a Repository instance.

        Args:
            as_client (ArchivesSpaceClient): The ArchivesSpace client instance.
            repo (asnake.jsonmodel.JSONModelObject): The ArchivesSpace repository object.
            timestamp (int): The Unix timestamp to filter updated resources.
        """
        self.as_client = as_client
        self.repo = repo
        self.timestamp = timestamp
        self.email_message = ""
        self.published_resources = []
        self.unpublished_resources = []

    def get_report(self):
        """Generates the report for the current repository.

        This method updates the lists of published and unpublished resources
        and then constructs the email message specific to this repository.
        """
        self.get_updated_resources()
        self.construct_body()

    def get_updated_resources(self):
        """Updates the lists of published and unpublished resources."""
        for resource in self.updated_resources():
            if resource.publish:
                self.published_resources.append(f"{resource.title} ({resource.id_0})")
            else:
                self.unpublished_resources.append(f"{resource.title} ({resource.id_0})")

    def construct_body(self):
        """Constructs the email message body for the current repository.

        The message includes counts of published and unpublished resources
        and lists their titles and IDs.
        """
        if len(self.published_resources) + len(self.unpublished_resources) > 0:
            self.email_message = f"{len(self.published_resources)} published resource records and {len(self.unpublished_resources)} unpublished resource records updated in {self.repo.name}\n"
            for resource in self.published_resources:
                self.email_message += f"{resource}\n"
            for resource in self.unpublished_resources:
                self.email_message += f"{resource}\n"
            self.email_message += "\n"
        else:
            self.email_message = f"0 resource records updated in {self.repo.name}\n\n"

    def updated_resources(self):
        """Generates updated resource objects for the repository.

        Yields:
            asnake.jsonmodel.JSONModelObject: An ArchivesSpace resource that has
                been updated and is not suppressed.
        """
        resource_ids = self.as_client.aspace.client.get(
            f"/repositories/{self.repo.id}/resources",
            params={"all_ids": True, "modified_since": self.timestamp},
        ).json()
        for resource_id in resource_ids:
            resource = self.repo.resources(resource_id)
            if not resource.suppressed:
                yield resource
