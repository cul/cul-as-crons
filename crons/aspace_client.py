from asnake.aspace import ASpace
from asnake.utils import get_note_text


class ArchivesSpaceClient:
    """Handles communication with ArchivesSpace."""

    def __init__(self, baseurl, username, password):
        self.aspace = ASpace(baseurl=baseurl, username=username, password=password)

    def all_resources(self):
        """Get data about resources from all repos in AS.

        Yields:
          str: Full JSON of AS resource
        """
        for repo in self.aspace.repositories:
            for resource in repo.resources:
                yield resource.json()

    def accessions_from_repository(self, repo_id):
        """Get data about resources from a repository in AS.

        Args:
            repo_id (int): ASpace repository ID (e.g., 2)

        Yields:
          str: Full JSON of AS accession
        """
        repo = self.aspace.repositories(repo_id)
        for accession in repo.accessions:
            yield accession.json()

    def all_agents(self):
        """Get data about agents from all repos in AS.

        Yields:
          str: Full JSON of AS agent
        """
        for agent in getattr(self.aspace, "agents"):
            yield agent.json()

    def all_subjects(self):
        # TODO: use logic in all_agents
        """Get data about subjects from all repos in AS.

        Yields:
          str: Full JSON of AS subject
        """
        for subject in getattr(self.aspace, "subjects"):
            yield subject.json()

    def get_specific_note_text(self, resource_json, note_type):
        """Get text for all notes of one type for a resource.

        Args:
            resource_json (dict): ASpace resource
            note_type (str): type of note

        Returns:
            string: note text of all notes of indicated note type
        """
        notes = []
        for note in [n for n in resource_json["notes"] if n["type"] == note_type]:
            notes.append("".join(get_note_text(note, self.aspace.client)))
        return " ".join(notes)

    def get_extents(self, resource_json):
        """Get information from all extent statements."""
        extents = resource_json.get("extents")
        if extents:
            extent_list = [f"{ext['number']} {ext['extent_type']}" for ext in extents]
            return ", ".join(extent_list)
        else:
            return ""

    def get_new_marc_records(self, repo_id, timestamp):
        """Get MARC21 XML for resources that have been updated since a provided timestamp.

        Args:
            repo_id (int): ASpace repository ID (e.g., 2)
            timestamp (int): A UTC timestamp coerced to an integer

        Yields:
            string: MARC21 XML for ASpace resource
        """
        resource_ids = self.aspace.client.get(
            f"/repositories/{repo_id}/resources",
            params={"all_ids": True, "modified_since": timestamp},
        ).json()
        for resource_id in resource_ids:
            marc_xml = self.aspace.client.get(
                f"/repositories/{repo_id}/resources/marc21/{resource_id}.xml"
            ).content.decode("utf-8")
            yield marc_xml
