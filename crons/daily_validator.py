from configparser import ConfigParser

from cul_archives_utils.clio_utils import ClioUtils
from dacsspace.validator import Validator

from .aspace_client import ArchivesSpaceClient
from .helpers import yesterday_utc


class ValidatorException(Exception):
    pass


class DailyValidator(object):
    """Runs validation across a repository for updated (or new) resource records."""

    def __init__(self):
        self.config_file = "local_settings.cfg"
        self.config = ConfigParser()
        self.config.read(self.config_file)
        self.as_client = ArchivesSpaceClient(
            self.config["ArchivesSpace"]["baseurl"],
            self.config["ArchivesSpace"]["username"],
            self.config["ArchivesSpace"]["password"],
        )

    def run(self):
        new_resources = self.as_client.get_new_resources(
            2, yesterday_utc()
        )  # change this to 48 hours
        for resource in new_resources:
            ResourceValidator(resource).run()


class ResourceValidator(object):
    """Validates a resource record  in ArchivesSpace.

    Only validates records if they have a published record in CLIO.
    """

    def __init__(self, resource):
        self.config_file = "local_settings.cfg"
        self.config = ConfigParser()
        self.config.read(self.config_file)
        self.as_client = ArchivesSpaceClient(
            self.config["ArchivesSpace"]["baseurl"],
            self.config["ArchivesSpace"]["username"],
            self.config["ArchivesSpace"]["password"],
        )
        self.resource = resource

    def run(self):
        print(f"checking if {self.resource.title} is in CLIO...")
        if self.published_in_clio():
            print(f"{self.resource.title} is in CLIO. Checking DACS compliance...")
            try:
                print(self.dacs_compliance())
                print("Checking whether agents are published...")
                self.check_published_agents()
            except ValidatorException as e:
                print(e)
        else:
            print(f"{self.resource.title} is NOT in CLIO.")

        # check all top level fields for whitespace only, delete
        # check all top level fields for leading and trailing whitespace; change or add if needed
        # check all children for leading and trailing whitespace in any fields; change or add if needed
        # check archival object titles for any line breaks; automatically replace linbreaks with comma
        # * Access notes do not contain correct onsite/offsite terminology _Action: manual intervention?_
        # ADD TO TICKET: check that normalized dates conform to ISO
        pass

    def published_in_clio(self):
        try:
            if self.resource.json().get("id_0"):
                bibid = self.resource.json()["id_0"]
                if ClioUtils().check_clio_status(bibid) == 200:
                    return True
                else:
                    return False
            else:
                return False
        except Exception:
            return False

    def dacs_compliance(self):
        validator = Validator("cul.json", None)
        result = validator.validate_data(self.resource.json())
        if result["valid"] is True:
            return True
        else:
            print(result)
            raise ValidatorException(result["explanation"])

    def check_published_agents(self):
        unpublished_agents = [a for a in self.resource.linked_agents if not a.publish]
        if not unpublished_agents:
            for ua in unpublished_agents:
                match = [
                    x
                    for x in self.resource.json().get("linked_agents")
                    if ua.ref == x["ref"]
                ][0]
                if match:
                    print(f"Unpublished agent found: {ua.ref}")
                    # self.as_client.publish_agent(ua)
