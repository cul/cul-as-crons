import argparse

from crons.fa_list_generator import FindingAidLists


def main():
    FindingAidLists().create_all_lists()


if __name__ == "__main__":
    main()
