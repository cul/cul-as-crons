from configparser import ConfigParser

from dacsspace.validator import Validator

from .aspace_client import ArchivesSpaceClient
from .helpers import yesterday_utc


class ValidatorException(Exception):
    pass


class DailyValidator(object):
    """Validates updated (or new) published resource records in ArchivesSpace."""

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
        new_resources = self.as_client.get_new_resources(2, yesterday_utc())
        for resource in new_resources:
            try:
                self.dacs_compliance(resource)
            except ValidatorException as e:
                print(e)

        # get new or updated published records
        # for each record:
        # validate for DACS single level minimum compliance; flag if needed
        # check that linked agents are published, publish if needed
        # check that citation is standard and exists; change or add if needed
        # check that access notes contain correct terminology; flag if incorrent
        # check all top level fields for whitespace only, delete
        # check all top level fields for leading and trailing whitespace; change or add if needed
        # check all children for leading and trailing whitespace in any fields; change or add if needed
        # check archival object titles for any line breaks; automatically replace linbreaks with comma
        # * Access notes do not contain correct onsite/offsite terminology _Action: manual intervention?_
        pass

    def dacs_compliance(self, resource):
        validator = Validator("cul.json", None)
        result = validator.validate_data(resource.json())
        if result["valid"] is True:
            return True
        else:
            print(result)
            raise ValidatorException(result["explanation"])
