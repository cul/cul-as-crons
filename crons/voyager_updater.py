from configparser import ConfigParser
from pathlib import Path

from .aspace_client import ArchivesSpaceClient
from .helpers import validate_against_schema, yesterday_utc


class UpdateAllInstances(object):
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

    def all_repos(self):
        """Iterates through each repository in each ASpace instance."""
        for instance_name in self.config.sections():
            as_client = ArchivesSpaceClient(
                self.config[instance_name]["baseurl"],
                self.config[instance_name]["username"],
                self.config[instance_name]["password"],
            )
            for repo in as_client.aspace.repositories:
                print(f"Updating {repo.name}")
                UpdateRepository(as_client, repo).updated_marc()


class UpdateRepository(object):
    def __init__(self, as_client, repo):
        self.export_params = {
            "include_unpublished": False,
            "include_daos": True,
        }
        self.as_client = as_client
        self.repo = repo

    def updated_marc(self, timestamp=None):
        """Gets MARCXML for recently updated records."""
        timestamp = yesterday_utc() if timestamp is None else timestamp
        for resource in self.updated_resources(timestamp):
            bibid = self.get_bibid(resource)
            # TODO: skip if validation failed?
            # XML schema: http://www.loc.gov/MARC21/slim http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd
            if bibid:
                try:
                    marc_response = self.as_client.aspace.client.get(
                        f"/repositories/{self.repo.id}/resources/marc21/{resource.id}.xml"
                    )
                    if not validate_against_schema(marc_response.content, "MARC21slim"):
                        print(f"{bibid}: Invalid MARC")
                    # print(bibid)
                    # print(marc)
                except Exception as e:
                    print(bibid, e)

    def all_cul(self):
        # add 965noexportAUTH to 965
        # make sure bibid is 001 tag, not 099 tag
        pass

    def cul_except_books(self):
        # <controlfield tag="003">NNC</controlfield>
        # reformat 035 CULASPC to local practice - <datafield ind1=" " ind2=" " tag="035"><subfield code="a"><xsl:text>(NNC)CULASPC:voyager:</xsl:text><xsl:value-of select="normalize-space(substring-after(., '-'))"/></subfield></datafield>
        pass

    def barnard(self):
        # maybe: add 965noexportAUTH to 965
        # make sure bibid is 001 tag,
        # match default 035 with what's in barnard
        # overall -- review our customizations
        pass

    def updated_resources(self, timestamp):
        resource_ids = self.as_client.aspace.client.get(
            f"/repositories/{self.repo.id}/resources",
            params={"all_ids": True, "modified_since": timestamp},
        ).json()
        for resource_id in resource_ids:
            resource = self.repo.resources(resource_id)
            if resource.publish and not resource.suppressed:
                yield resource

    def get_bibid(self, resource):
        if resource.id_0.isnumeric():
            return resource.id_0
        elif resource.user_defined.integer_1.isnumeric():
            return resource.user_defined.integer_1
        else:
            return False
