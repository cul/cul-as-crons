import argparse

from crons.acfa_updater import UpdateAllInstances


def main():
    parser = argparse.ArgumentParser(
        description="Exports EAD files from all ASpace instances in config file to a directory and deletes related HTML files"
    )
    parser.add_argument("api_key", help="API key for finding aids API")
    parser.add_argument("parent_cache", help="Parent directory of EAD and HTML caches")
    args = parser.parse_args()
    UpdateAllInstances(args.parent_cache).all_repos(args.api_key)


if __name__ == "__main__":
    main()
