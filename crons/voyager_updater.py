from configparser import ConfigParser
from pathlib import Path

from lxml import etree

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
                    marc_record = MarcRecord(bibid, marc_response)
                    if not marc_record.validate_marc:
                        print(f"{bibid}: Invalid MARC")
                    # marc_root = etree.fromstring(marc_response.content)
                    # yield marc_root
                    yield marc_response.content
                    # print(bibid)
                    # print(marc)
                except Exception as e:
                    print(bibid, e)

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
        elif getattr(resource, "user_defined"):
            if getattr(resource.user_defined, "integer_1"):
                return resource.user_defined.integer_1
            else:
                return False
        else:
            return False


class MarcRecord(object):
    """docstring for MarcRecord"""

    def __init__(self, bibid, marc_response):
        """Set up MARC record.

        Args:
            marc_response (obj): response from ASpace API
        """
        self.bibid = bibid
        self.marc_record = etree.fromstring(marc_response.content)
        self.namespaces = {None: "http://www.loc.gov/MARC21/slim"}

    def validate_marc(self):
        validate_against_schema(self.marc_response.content, "MARC21slim")

    def all_records(self):
        # make sure bibid is in 001 tag
        # update leader
        # QUESTION: do we need to change namespace?
        pass

    def add_controlfield_001(self):
        if not self.marc_record.find(
            ".//controlfield[@tag='001']", namespaces=self.namespaces
        ):
            leader_element = self.marc_record.find(
                ".//leader", namespaces=self.namespaces
            )
            leader_element_index = leader_element.getparent().index(leader_element)
            controlfield_001 = etree.Element("controlfield", tag="001")
            controlfield_001.text = self.bibid
            leader_element.getparent().insert(
                leader_element_index + 1, controlfield_001
            )

    def add_controlfield_003(self):
        if not self.marc_record.find(
            ".//controlfield[@tag='003']", namespaces=self.namespaces
        ):
            controlfield_003 = etree.Element("controlfield", tag="003")
            controlfield_003.text = "NNC"
            controlfield_001 = self.marc_record.find(
                ".//controlfield[@tag='001']", namespaces=self.namespaces
            )
            controlfield_001_index = controlfield_001.getparent().index(
                controlfield_001
            )
            controlfield_001.getparent().insert(
                controlfield_001_index + 1, controlfield_003
            )

    def update_datafield_035_culaspc(self):
        datafield_035_subfield_a = self.marc_record.find(
            ".//datafield[@tag='035']/subfield[@code='a']", namespaces=self.namespaces
        )
        if datafield_035_subfield_a.text == f"CULASPC-{self.bibid}":
            datafield_035_subfield_a.text = f"(NNC)CULASPC:voyager:{self.bibid}"

    def update_datafield_100(self):
        datafield_100 = self.marc_record.find(
            './/datafield[@tag="100"]', namespaces=self.namespaces
        )
        subfield_d = datafield_100.find(
            './subfield[@code="d"]', namespaces=self.namespaces
        )
        if subfield_d:
            subfield_d.text = subfield_d.text.rstrip(
                ",."
            )  # Remove trailing comma or period
        # TODO: do we need to remove punctuation from subfield_a if there's no subfield_d?
        subfield_e = datafield_100.find(
            './subfield[@code="e"]', namespaces=self.namespaces
        )
        if subfield_e:
            datafield_100.remove(subfield_e)

    def update_datafield_856(self):
        datafield_856 = self.marc_record.find(
            './/datafield[@tag="856"]', namespaces=self.namespaces
        )
        subfield_z = datafield_856.find(
            './subfield[@code="z"]', namespaces=self.namespaces
        )
        if subfield_z:
            datafield_856.remove(subfield_z)
        subfield_3 = etree.Element("subfield", code="3")
        subfield_3.text = "Finding aid"
        datafield_856.append(subfield_3)

    def add_965noexportAUTH(self):
        datafield_965 = etree.Element("datafield", tag="965")
        subfield_a = etree.Element("subfield", code="a")
        subfield_a.text = "965noexportAUTH"
        datafield_965.append(subfield_a)
        self.marc_record[0].append(datafield_965)

    def cul(self):
        # add 965noexportAUTH to 965
        # update 856
        # make sure bibid is 001 tag, not 099 tag
        # <controlfield tag="003">NNC</controlfield>
        # reformat 035 CULASPC to local practice
        pass

    def barnard(self):
        # TODO: ask LIT - are we adding 003 for barnard?
        # maybe: add 965noexportAUTH to 965
        # make sure bibid is 001 tag,
        # match default 035 with what's in barnard
        # overall -- review our customizations
        # ask about OCoLC numbers
        pass
