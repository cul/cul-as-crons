from asnake.aspace import ASpace
from asnake.utils import get_note_text

import time


class ArchivesSpaceClient:
    """Handles communication with ArchivesSpace."""

    def __init__(self, baseurl, username, password):
        self.aspace = ASpace(baseurl=baseurl, username=username, password=password)

    def updated_resources(self, timestamp):
        resource_ids = self.as_client.aspace.client.get(
            f"/repositories/{self.repo.id}/resources",
            params={"all_ids": True, "modified_since": timestamp},
        ).json()
        for resource_id in resource_ids:
            resource = self.repo.resources(resource_id)
            if resource.publish and not resource.suppressed:
                yield resource

    def create_pdf_job(self, resource_id):
        data = {
            "jsonmodel_type": "job",
            "status": "queued",
            "has_modified_records": False,
            "inactive_record": False,
            "job": {
                "jsonmodel_type": "print_to_pdf_job",
                "source": f"/repositories/{self.repo.id}/resources/{resource_id}",
                "include_unpublished": False,
            },
        }
        response = self.as_client.aspace.client.post(
            f"repositories/{self.repo.id}/jobs", json=data
        )
        response.raise_for_status()
        job_uri = response.json().get("uri")
        job_json = self.as_client.aspace.client.get(job_uri).json()
        start_time = time.time()
        max_minutes = 15
        while True:
            job_json = self.as_client.aspace.client.get(job_uri).json()
            if time.time() - start_time >= max_minutes * 60:
                raise Exception(f"Job timed out after {max_minutes} minutes")
            elif job_json["status"] == "completed":
                output_file_id = self.as_client.aspace.client.get(
                    f"{job_uri}/output_files"
                ).json()[0]
                pdf_response = self.as_client.aspace.client.get(
                    f"{job_uri}/output_files/{output_file_id}"
                )
                return pdf_response
            elif job_json["status"] == "failed":
                raise Exception("PDF export failed!")
            else:
                time.sleep(1)

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
        for note in [n for n in resource_json["notes"] if n.get("type") == note_type]:
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

    def get_json_response(self, uri):
        """Get JSON response for ASpace get request

        Args:
            uri (str): ASpace URI
        """
        response = self.aspace.client.get(uri)
        return response.json()

    def published_resources(self, repo_id):
        for resource in self.aspace.repositories(repo_id).resources:
            if resource.publish and not resource.suppressed:
                if resource.json().get("ead_location"):
                    yield resource
