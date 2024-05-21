import logging
from configparser import ConfigParser
from pathlib import Path

from crons.aspace_client import ArchivesSpaceClient
from crons.helpers import format_date


class FindingAidLists(object):
    def __init__(self):
        current_path = Path(__file__).parents[1].resolve()
        self.config_file = Path(current_path, "local_settings.cfg")
        self.config = ConfigParser()
        self.config.read(self.config_file)
        self.as_client = ArchivesSpaceClient(
            self.config["ArchivesSpace"]["baseurl"],
            self.config["ArchivesSpace"]["username"],
            self.config["ArchivesSpace"]["password"],
        )
        self.base_path = self.config["Other"]["finding_aids_lists"]
        logging.basicConfig(
            datefmt="%m/%d/%Y %I:%M:%S %p",
            format="%(asctime)s %(message)s",
            level=logging.INFO,
            handlers=[
                logging.FileHandler("finding_aid_lists.log"),
                logging.StreamHandler(),
            ],
        )

    def create_all_lists(self):
        """Creates html snippets of finding aid lists for all CUL repositories."""
        logging.info("Starting process...")
        try:
            repositories = {3: "nnc-a", 4: "nnc-ea", 5: "nnc-ut"}
            for repo_id, repo_code in repositories.items():
                resource_links = {}
                for resource in self.as_client.published_resources(repo_id):
                    title = self.construct_title(resource)
                    resource_links[title] = self.create_resource_link(
                        repo_code, resource.id_0, title
                    )
                self.create_html_snippet(resource_links, repo_code)
            rbml_links = {}
            ua_links = {}
            oh_links = {}
            for resource in self.as_client.published_resources(2):
                title = self.construct_title(resource)
                rbml_code = "nnc-rb"
                ua_code = "nnc-ua"
                oh_code = "nnc-ccoh"
                call_number = (
                    resource.json().get("user_defined", {}).get("string_1", "")
                )
                if call_number.startswith("UA"):
                    ua_links[title] = self.create_resource_link(
                        ua_code, resource.id_0, title
                    )
                elif call_number.startswith("OH"):
                    oh_links[title] = self.create_resource_link(
                        oh_code, resource.id_0, title
                    )
                else:
                    rbml_links[title] = self.create_resource_link(
                        rbml_code, resource.id_0, title
                    )
            self.create_html_snippet(rbml_links, rbml_code)
            self.create_html_snippet(ua_links, ua_code)
            for resource in self.as_client.published_resources(7):
                title = self.construct_title(resource)
                oh_links[title] = self.create_resource_link(
                    oh_code, resource.id_0, title
                )
            self.create_html_snippet(oh_links, oh_code)
        except Exception as e:
            logging.error(e)

    def create_resource_link(self, repo_code, bibid, title):
        return f'<li><a href="/ead/{repo_code}/ldpd_{bibid}">{title}</a></li>'

    def create_html_snippet(self, links_dict, repo_code):
        """Writes an HTML unordered list to a file.

        links_dict (dict): finding aid titles (keys) and HTML link elements (values)
        repo_code (str): CUL repository code (e.g., nnc-rb)
        """
        links_dict = dict(sorted(links_dict.items()))
        with open(f"{self.base_path}/{repo_code}_fa_list.html", "w") as f:
            f.write("<ul>\n")
            for link in links_dict.values():
                f.write(f"{link}\n")
            f.write("</ul>")

    def construct_title(self, resource):
        """Creates a finding aid title, including a formatted date.

        resource (obj): ArchivesSnake resource object
        """
        title = resource.title if resource.title.endswith(",") else f"{resource.title},"
        bulk_dates = []
        if resource.dates:
            first_date = resource.dates[0].json()
            date_string = format_date(first_date)
            if len(resource.dates) > 1:
                bulk_dates = [x for x in resource.dates if x.date_type == "bulk"]
                bulk_date_string = (
                    format_date(bulk_dates[0].json()) if bulk_dates else None
                )
            if bulk_dates:
                return f"{title} {date_string} (bulk {bulk_date_string})"
            else:
                return f"{title} {date_string}"
        else:
            return resource.title
