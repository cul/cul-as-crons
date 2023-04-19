from configparser import ConfigParser
from pathlib import Path

from crons.aspace_client import ArchivesSpaceClient


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

    def run(self):
        repositories = {3: "nnc-a", 4: "nnc-ea", 5: "nnc-ut"}
        for repo_id, repo_code in repositories.items():
            resource_links = {}
            for resource in self.as_client.published_resources(repo_id):
                title = self.construct_title(resource)
                resource_link = f'<li><a href="/ead/{repo_code}/ldpd_{resource.id_0}">{title}</a></li>'
                resource_links[title] = resource_link
            self.create_html_snippet(resource_links, repo_code)
        rbml_links = {}
        ua_links = {}
        oh_links = {}
        for resource in self.as_client.published_resources(2):
            title = self.construct_title(resource)
            rbml_code = "nnc-rb"
            ua_code = "nnc-ua"
            oh_code = "nnc-ccoh"
            call_number = resource.json().get("user_defined", {}).get("string_1", "")
            if call_number.startswith("UA"):
                resource_link = f'<li><a href="/ead/{ua_code}/ldpd_{resource.id_0}">{title}</a></li>'
                ua_links[title] = resource_link
            elif call_number.startswith("OH"):
                resource_link = f'<li><a href="/ead/{oh_code}/ldpd_{resource.id_0}">{title}</a></li>'
                oh_links[title] = resource_link
            else:
                resource_link = f'<li><a href="/ead/{rbml_code}/ldpd_{resource.id_0}">{title}</a></li>'
                rbml_links[title] = resource_link
        self.create_html_snippet(rbml_links, rbml_code)
        self.create_html_snippet(ua_links, ua_code)
        for resource in self.as_client.published_resources(7):
            title = self.construct_title(resource)
            resource_link = (
                f'<li><a href="/ead/{oh_code}/ldpd_{resource.id_0}">{title}</a></li>'
            )
            oh_links[title] = resource_link
        self.create_html_snippet(oh_links, oh_code)

    def create_html_snippet(self, links_dict, repo_code):
        links_dict = dict(sorted(links_dict.items()))
        with open(f"{self.base_path}/{repo_code}_fa_list.html", "w") as f:
            f.write("<ul>\n")
            for link in links_dict.values():
                f.write(f"{link}\n")
            f.write("</ul>")

    def construct_title(self, resource):
        title = resource.title if resource.title.endswith(",") else f"{resource.title},"
        bulk_dates = []
        if resource.dates:
            first_date = resource.dates[0].json()
            date_string = self.format_date(first_date)
            if len(resource.dates) > 1:
                bulk_dates = [x for x in resource.dates if x.date_type == "bulk"]
                bulk_date_string = (
                    self.format_date(bulk_dates[0].json()) if bulk_dates else None
                )
            if bulk_dates:
                return f"{title} {date_string} (bulk {bulk_date_string})"
            else:
                return f"{title} {date_string}"
        else:
            return resource.title

    def format_date(self, date_json):
        if date_json.get("expression"):
            date_string = date_json["expression"]
        else:
            date_string = date_json["begin"]
            if date_json.get("end"):
                date_string = f"{date_json['begin']}-{date_json['end']}"
        return date_string
