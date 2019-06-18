import re
import sys
import getopt
import os
from loggingcfg import initialize_logger
from utils import utility
import pandas as pd

regex = r'(\S+\/\S+)(#\d+|@\d+)'


def __replace(_str):
    _ref = _str.replace("(", "")
    _ref = _ref.replace(")", "")
    _ref = _ref.replace("[", "")
    _ref = _ref.replace("]", "")
    return _ref


def __extract(input_dir_path: str, commit_pattern: str = "*commit*.csv", issue_pattern: str = "*comments.csv"):
    logger.info("Retrieving comments from commits")
    commit_messages = utility.read_from_folder(input_dir_path, commit_pattern, ["SLUG", "MESSAGE"])
    logger.info("Extracting cross refs from commit messages")
    cross_references = []

    for cm in commit_messages.itertuples():
        cross_refs = re.finditer(regex, getattr(cm, "MESSAGE"), re.MULTILINE)
        slug = getattr(cm, "SLUG")
        for ref in cross_refs:
            if slug not in ref.group(0):
                _ref = __replace(ref.group(0))
                cross_references.append([slug, _ref, "commit"])

    logger.info("Retrieving comments from issues and pull-requests")
    issuepr_messages = utility.read_from_folder(input_dir_path, issue_pattern, ["SLUG", "BODY"])
    logger.info("Extracting cross refs from issue/PR messages")
    for ipr in issuepr_messages.itertuples():
        cross_refs = re.finditer(regex, getattr(ipr, "BODY"), re.MULTILINE)
        slug = getattr(ipr, "SLUG")
        for ref in cross_refs:
            if slug not in ref.group(0):
                _ref = __replace(ref.group(0))
                cross_references.append([slug, _ref, "issue/pr"])

    logger.info("Saving cross references")
    df = pd.DataFrame(cross_references, columns=["SLUG", "REF", "TYPE"])
    df.to_csv(os.path.join(input_dir_path, "cross_references.csv"), index=False)


if __name__ == '__main__':
    logger = initialize_logger(name="CROSS_REF")
    help_message = 'Usage:\n extractor.py -in|--input=<input_dir> -cp|--commit_pattern=<commit_pattern_file> -ip|--issues_pattern=<issues_pattern_file>'
    input_dir = None
    commit_pattern = "*blamed_commit.csv"
    issues_pattern = "*comments.csv"

    try:
        if not sys.argv[1:]:
            raise getopt.GetoptError('No arguments passed from the command line. See help instructions.')
        opts, args = getopt.getopt(sys.argv[1:], "H:in:cp:ip", ["input=", "commit_pattern=", "issues_pattern=", "help"])
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print(help_message)
                sys.exit(0)
            elif opt in ("-in", "--input"):
                input_dir = arg
            elif opt in ("-cp", "--commit_pattern"):
                commit_pattern = arg
            elif opt in ("-ip", "--issues_pattern"):
                issues_pattern = arg
            else:
                assert False, "unhandled option"
    except getopt.GetoptError as err:
        # print help information and exit:
        logger.error(err)  # will print something like "option -a not recognized"
        print(help_message)
        sys.exit(1)

    try:
        __extract(input_dir, commit_pattern, issues_pattern)
        logger.info("Done")
    except KeyboardInterrupt:
        logger.error("Received Ctrl-C or another break signal. Exiting.")
