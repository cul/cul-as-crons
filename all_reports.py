import argparse

from crons.report_accessions import AccessionsReporter
from crons.report_agents import AgentsReporter
from crons.report_subjects import SubjectReporter
from crons.resource_reporter import ResourceReporter


def main():
    print("hello")
    parser = argparse.ArgumentParser(
        description="Generates reports against ArchivesSpace API"
    )
    parser.add_argument("--google_sheets", action="store_true")
    args = parser.parse_args()
    ResourceReporter().run(args.google_sheets)
    AccessionsReporter().run(args.google_sheets)
    AgentsReporter().run(args.google_sheets)
    SubjectReporter().run(args.google_sheets)

if __name__ == "__main__":
    main()