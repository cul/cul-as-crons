import logging
from configparser import ConfigParser

from cul_archives_utils.clio_utils import ClioUtils
from dacsspace.validator import Validator

from .aspace_client import ArchivesSpaceClient
from .helpers import (
    DateException,
    check_date,
    empty_values,
    leading_trailing,
    yesterday_utc,
)


class ValidatorException(Exception):
    pass


class DailyValidator(object):
    def __init__(self):
        logging.basicConfig(
            datefmt="%m/%d/%Y %I:%M:%S %p",
            format="%(asctime)s %(message)s",
            level=logging.INFO,
            handlers=[
                logging.FileHandler("daily_validator.log"),
                logging.StreamHandler(),
            ],
        )
        self.config_file = "local_settings.cfg"
        self.config = ConfigParser()
        self.config.read(self.config_file)
        self.as_client = ArchivesSpaceClient(
            self.config["ArchivesSpace"]["baseurl"],
            self.config["ArchivesSpace"]["username"],
            self.config["ArchivesSpace"]["password"],
        )

    def run(self):
        """Run validation across a repository for updated (or new) resource records."""
        new_resources = self.as_client.get_new_resources(
            2, yesterday_utc()
        )  # change this to 48 hours
        for resource in new_resources:
            ResourceValidator(resource).run()


class ResourceValidator(object):
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
        """Validates a resource record  in ArchivesSpace.

        Only validates records if they have a published record in CLIO.
        """
        print(f"checking if {self.resource.title} is in CLIO...")
        if self.published_in_clio():
            print(f"{self.resource.title} is in CLIO. Checking DACS compliance...")
            try:
                print(self.dacs_compliance())
                # TODO: save resource json somewhere
                self.resource_json = self.resource.json()
                print("Checking whether agents are published...")
                self.check_published_agents()
                print(
                    "Checking whether there are whitespace only resource level fields..."
                )
                self.remove_whitespace_resource()
                print(
                    "Checking whether there is leading and trailing whitespace in resource level fields..."
                )
                self.remove_trailing_resource()
                print("Checking that resource dates are valid...")
                self.check_dates(self.resource_json["dates"])
                print("Checking children...")
                self.check_children()
            except ValidatorException as e:
                print(e)
            except DateException as e:
                print(e)
        else:
            print(f"{self.resource.title} is NOT in CLIO.")

        # * Access notes do not contain correct onsite/offsite terminology _Action: manual intervention?_

    def check_access_note(self):
        pass

    def check_children(self):
        children = self.as_client.get_all_children(self.resource)
        for child in children:
            fields_with_whitespace = leading_trailing(child)
            for field in fields_with_whitespace:
                # self.as_client.update_aspace_field(child, field, child[field].strip())
                child = self.as_client.get_json_response(child["uri"])
                print(field, child["display_string"])
            if child.get("title"):
                without_linebreaks = (
                    child["title"].replace("\r\n", " ").replace("\n", " ")
                )
                if child["title"] != without_linebreaks:
                    # self.as_client.update_aspace_field(child, "title", without_linebreaks)
                    child = self.as_client.get_json_response(child["uri"])
            new_dates = []
            dates = child["dates"]
            if dates:
                try:
                    for date in dates:
                        date = check_date(date)
                        new_dates.append(date)
                    if new_dates != dates:
                        print(new_dates)
                        # self.as_client.update_aspace_field(child, "dates", new_dates)
                        child = self.as_client.get_json_response(child["uri"])
                except DateException as e:
                    raise e

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
            raise ValidatorException(result["explanation"])

    def check_published_agents(self):
        unpublished_agents = [a for a in self.resource.linked_agents if not a.publish]
        if not unpublished_agents:
            for ua in unpublished_agents:
                match = [
                    x
                    for x in self.resource_json.get("linked_agents")
                    if ua.ref == x["ref"]
                ][0]
                if match:
                    print(f"Unpublished agent found: {ua.ref}")
                    # self.as_client.publish_agent(ua)

    def remove_whitespace_resource(self):
        """Check all top level fields for whitespace only, delete."""
        fields_with_whitespace = empty_values(self.resource_json)
        for field in fields_with_whitespace:
            print(field)
            # self.as_client.update_aspace_field(self.resource_json, field, None)

    def remove_trailing_resource(self):
        """Check all top level fields for leading and trailing whitespace."""
        fields_with_whitespace = leading_trailing(self.resource_json)
        for field in fields_with_whitespace:
            print(field)
            # self.as_client.update_aspace_field(self.resource_json, field, self.resource_json[field].strip())

    def check_dates(self, dates):
        new_dates = []
        dates = self.resource_json["dates"]
        if dates:
            try:
                for date in dates:
                    date = check_date(date)
                    new_dates.append(date)
                if new_dates != dates:
                    print(new_dates)
                    # self.as_client.update_aspace_field(
                    #     self.resource_json, "dates", new_dates
                    # )
            except DateException as e:
                raise e
