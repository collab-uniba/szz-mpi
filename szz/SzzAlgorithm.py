import os
import sys
import getopt

import logging

import numpy as np
import pygit2
import pytz

import loggingcfg
from szz.Issue import Issue, from_csv
from githubutils.CommitWrapper import CommitWrapper
from activityclassifier import BasicFileTypeClassifier
from szz.SzzCommit import SzzCommit
from szz.SzzPatch import SzzPatch
from szz.SzzHunk import SzzHunk
from szz.BlamedCommit import BlamedCommit
from szz.SzzContributor import SzzContributor
from szz.Blame import Blame
from szz.Commit import Commit

from typing import Dict
from mpi4py import MPI
from typing import List

import time
import traceback
import hashlib
import pandas as pd
import itertools
from utils import utility

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
mpisize = comm.Get_size()

log = loggingcfg.initialize_logger('SZZ-MPI', console_level=logging.INFO)


class Szz:
    __COMMIT_COLUMNS = ["SLUG", "SHA", "TIMESTAMP", "AUTHOR_ID", "COMMITTER_ID", "MESSAGE",
                        "NUM_PARENTS",
                        "NUM_ADDITIONS", "NUM_DELETIONS", "NUM_FILES_CHANGED", "FILES",
                        "SRC_LOC_ADDED",
                        "SRC_LOC_DELETED", "NUM_SRC_FILES_TOUCHED", "SRC_FILES"]

    def __init__(self, repo_path: str, issues_file_path: str, output_folder: str, valid_labels: List[str],
                 max_num_files_changed=50, max_new_lines=200):
        self.__repo_path = repo_path
        self.__output_folder = output_folder
        self.__issues_dict: Dict[int, Issue] = from_csv(issues_file_path)
        self.__valid_labels = valid_labels
        self.__basic_classifier = BasicFileTypeClassifier()
        self.__slug = utility.folder_name_to_slug(repo_path)
        self.__max_num_files_changed = max_num_files_changed
        self.__max_new_lines = max_new_lines
        self.__slug_unslashed = self.__slug.replace("/", "_")
        self.__contributors = {}
        self.__mpi_enabled = mpisize > 1

    def __commit_to_metadata(self, commit: Commit):
        return [self.__slug, commit.sha, commit.timestamp, commit.author_id, commit.committer_id,
                commit.message, commit.num_parents,
                commit.num_additions, commit.num_deletions, commit.num_files_changed,
                commit.files, commit.src_loc_added,
                commit.src_loc_deleted, commit.num_src_files_touched, commit.src_files]

    def __commit_wrapper_to_commit(self, commit: CommitWrapper, git_repo: pygit2.Repository,
                                   contributors: Dict) -> Commit:
        sha = commit.sha

        authored_datetime = commit.authored_date

        (author_name, author_email) = commit.author
        (author_name_l, author_email_l) = (author_name.lower(), author_email.lower())
        (committer_name, committer_email) = commit.committer
        (committer_name_l, committer_email_l) = (committer_name.lower(), committer_email.lower())

        if (author_name_l, author_email_l) not in contributors:
            author_id = Szz.__hash_values(self, author_name_l, author_email_l)
            contributors[author_id] = (author_name_l, author_email_l)

        if (committer_name_l, committer_email_l) not in contributors:
            committer_id = Szz.__hash_values(self, committer_name_l, committer_email_l)
            contributors[committer_id] = (committer_name_l, committer_email_l)

        message = commit.message.strip()
        diff = commit.diff(git_repo)
        loc_added = diff.stats.insertions
        loc_deleted = diff.stats.deletions
        num_files_touched = diff.stats.files_changed

        # get info about changes to src files in the new  commit
        all_files, src_files, num_src_files_touched, src_loc_added, src_loc_deleted = \
            CommitWrapper.get_src_changes(self.__basic_classifier, diff)

        db_commit = Commit(sha,
                           authored_datetime,
                           author_id,
                           committer_id,
                           message,
                           len(commit.parents),
                           loc_added,
                           loc_deleted,
                           num_files_touched,
                           all_files,
                           src_loc_added,
                           src_loc_deleted,
                           num_src_files_touched,
                           src_files)

        return db_commit

    @staticmethod
    def __fetch_hunks(self, git_repo: pygit2.Repository) -> List[SzzHunk]:
        szz_hunks = []
        issue_links = []
        commits = []
        contributors = {}
        commit_files = []
        for c in git_repo.walk(git_repo[git_repo.head.target].id, pygit2.GIT_SORT_TIME):
            commit = CommitWrapper(c)

            authored_datetime = commit.authored_date

            if len(commit.parents) > 0:
                commits.append(
                    self.__commit_to_metadata(self.__commit_wrapper_to_commit(commit, git_repo, contributors)))
                closes_valid_issue = False
                if commit.message is not None:
                    commit_issue_ids = commit.issue_ids
                    if len(commit_issue_ids) > 0:
                        for (line_num, issue_ids) in commit_issue_ids:
                            for issue_id in issue_ids:
                                issue = self.__issues_dict.get(issue_id)
                                if issue:

                                    delta_open = (
                                            authored_datetime - issue.created_at.replace(
                                        tzinfo=pytz.utc)).total_seconds()

                                    if issue.closed_at is not None:
                                        delta_closed = (
                                                authored_datetime - issue.closed_at.replace(
                                            tzinfo=pytz.utc)).total_seconds()

                                    else:
                                        delta_closed = None

                                    issue_links.append(
                                        [self.__slug, commit.sha, line_num, issue.number, issue.is_pl, delta_open,
                                         delta_closed])
                                    
                                    """
                                        Valid issues are those
                                        1) for which the associated commit was registered *after* the issue was open (delta open > 0)
                                        2) for which the associated commit was registered *before or exactly when* the associated issue was closed
                                            (delta closed <= 0)
                                        3) are not pull requests (is_pr == 1), just issues (is_pr == 0)
                                    """
                                    if (not closes_valid_issue) and (delta_open > 0 >= delta_closed) and not issue.is_pl:
                                        if not issue.labels:  # no labels is fine
                                            closes_valid_issue = True
                                        else:
                                            for label in issue.labels:
                                                if label in self.__valid_labels:
                                                    closes_valid_issue = True
                                                    break

                szz_commit = SzzCommit(sha=commit.sha, sha_parent=commit.parents[0].hex)

                for patch in commit.diff(git_repo):
                    commit_file = os.path.basename(patch.delta.new_file.path)
                    lang = self.__basic_classifier.labelFile(commit_file)
                    loc_ins = 0
                    loc_del = 0

                    for hunk in patch.hunks:
                        for hl in hunk.lines:
                            if hl.origin == '-':
                                loc_del -= 1
                            elif hl.origin == '+':
                                loc_ins += 1

                    commit_files.append([self.__slug, commit.sha, commit_file, loc_ins, loc_del, lang])

                    # skip changes to binary files
                    if patch.delta.is_binary:
                        continue

                    old_file = patch.delta.old_file.path
                    label = self.__basic_classifier.labelFile(old_file)

                    # Ignore changes to documentation files
                    if label == self.__basic_classifier.DOC:
                        continue

                    if closes_valid_issue:
                        szz_patch = SzzPatch(old_file=old_file, label=label, commit=szz_commit)

                        for hunk in patch.hunks:
                            line_labels = {}
                            if hunk.old_lines:

                                for hl in hunk.lines:
                                    """
                                    only changes to deleted lines can be tracked back to when they were first introduced
                                    there is no parent commit that introduced a new line that it's being added in the current
                                    commit for the first time (ie, lines marked with a '+' in the diffs)

                                    this is not a basic SZZ implementation, as we classify changes at line level (e.g., skip changes
                                    to line of comments)
                                    """
                                    if hl.origin == '-':
                                        line_labels[hl.old_lineno] = self.__basic_classifier.labelDiffLine(
                                            hl.content.replace('\r', '').replace('\n', ''))

                                szz_hunk = SzzHunk(old_lines=hunk.old_lines, old_start=hunk.old_start, patch=szz_patch,
                                                   line_labels=line_labels)
                                szz_hunks.append(szz_hunk)

        total_hunks = len(szz_hunks)
        log.info("Total hunks to process: %d", total_hunks)

        self.__contributors = {key: SzzContributor(key, value[0], value[1]) for key, value in contributors.items()}

        log.info("Saving commits to csv")
        commits_df = pd.DataFrame(commits, columns=self.__COMMIT_COLUMNS)
        commits_df.to_csv(os.path.join(self.__output_folder, self.__slug_unslashed + "_commits.csv"), index=False)
        log.info("Saving commits to csv - COMPLETED")

        log.info("Saving commit files to csv")
        commit_files_df = pd.DataFrame(commit_files, columns=["SLUG", "SHA", "COMMIT_FILE", "LOC_INS", "LOC_DEL", "LANG"])
        commit_files_df.to_csv(os.path.join(self.__output_folder, self.__slug_unslashed + "_commit_files.csv"), index=False)
        log.info("Saving commit files to csv - COMPLETED")

        log.info("Saving issue_links to csv")
        issue_links_df = pd.DataFrame(issue_links,
                                      columns=["SLUG", "COMMIT_SHA", "LINE_NUM", "ISSUE_NUMBER", "ISSUE_IS_PL",
                                               "DELTA_OPEN", "DELTA_COLSED"])
        issue_links_df.to_csv(os.path.join(self.__output_folder, self.__slug_unslashed + "_issue_links.csv"),
                              index=False)
        log.info("Saving issue_links to csv - COMPLETED")

        return np.array_split(szz_hunks, min(mpisize, total_hunks))

    @staticmethod
    def __log_processing_time(self, message, start):
        processing_time = (time.time() - start) * 1000
        log.info(message + ": %.0f [ms]", processing_time)

    @staticmethod
    def __hash_values(self, first: str, second: str):
        return hashlib.md5(bytes(first + second, "utf8")).hexdigest()

    def __fetch_blamed_commits(self, szz_hunks, git_repo: pygit2.Repository) -> Dict[str, BlamedCommit]:
        log.info("Process %d starts blame_commit_process", rank)
        start = time.time()

        blamed_commits = {}
        contributors = {}
        blame_counter = {}

        for hunk in szz_hunks:

            line_labels = hunk.line_labels

            for bh in git_repo.blame(hunk.patch.old_file, newest_commit=hunk.patch.commit.sha_parent,
                                     min_line=hunk.old_start, max_line=hunk.old_start + hunk.old_lines - 1):
                blamed_sha = str(bh.final_commit_id)
                if blamed_sha not in blamed_commits:
                    try:
                        blamed_commit = CommitWrapper(git_repo.revparse_single(blamed_sha))

                        blamed_parents = blamed_commit.parents
                        blamed_num_parents = len(blamed_parents)

                        if not blamed_num_parents:
                            ins = None
                            dels = None
                            num_files = None
                        else:
                            blamed_diff = blamed_commit.diff(git_repo)
                            ins = blamed_diff.stats.insertions
                            dels = blamed_diff.stats.deletions
                            num_files = blamed_diff.stats.files_changed

                        if num_files is None or num_files >= self.__max_num_files_changed:
                            continue

                        if ins and ins >= self.__max_new_lines:
                            continue

                        blamed_authored_datetime = blamed_commit.authored_date

                        (blamed_author_name,
                         blamed_author_email) = blamed_commit.author
                        (blamed_author_name_l, blamed_author_email_l) = (
                            blamed_author_name.lower(), blamed_author_email.lower())

                        (blamed_committer_name,
                         blamed_committer_email) = blamed_commit.committer
                        (blamed_committer_name_l, blamed_committer_email_l) = (
                            blamed_committer_name.lower(), blamed_committer_email.lower())

                        if (blamed_author_name_l, blamed_author_email_l) not in contributors:
                            blamed_author_id = Szz.__hash_values(self, blamed_author_name_l, blamed_author_email_l)
                            contributors[blamed_author_id] = (blamed_author_name_l, blamed_author_email_l)

                        if (blamed_committer_name_l, blamed_committer_email_l) not in contributors:
                            blamed_committer_id = Szz.__hash_values(self, blamed_committer_name_l,
                                                                    blamed_committer_email_l)
                            contributors[blamed_committer_id] = (blamed_committer_name_l, blamed_committer_email_l)

                        blamed_message = blamed_commit.message
                        blamed_first_msg_line = blamed_message.split('\n')[0]

                        # get info about changes to src files in the new blamed commit
                        all_files, src_files, num_src_files_touched, src_loc_added, src_loc_deleted = \
                            CommitWrapper.get_src_changes(self.__basic_classifier,
                                                          blamed_commit.diff(git_repo))

                        blamed_commit = BlamedCommit(blamed_sha,
                                                     blamed_authored_datetime,
                                                     blamed_author_id,
                                                     blamed_committer_id,
                                                     blamed_first_msg_line,
                                                     blamed_num_parents,
                                                     ins,
                                                     dels,
                                                     num_files,
                                                     all_files,
                                                     src_loc_added,
                                                     src_loc_deleted,
                                                     num_src_files_touched,
                                                     src_files)

                        blamed_commits[blamed_sha] = (blamed_commit, hunk)

                    except Exception as e:
                        log.error(
                            msg="{0}: revparse error {1}:\t{2}".format(self.__repo_path, blamed_sha, e))
                        traceback.print_exc()

                for line_num in range(bh.final_start_line_number,
                                      bh.final_start_line_number + bh.lines_in_hunk):
                    if line_labels[line_num] == self.__basic_classifier.CG_CODE:
                        blame_counter.setdefault(blamed_sha, 0)
                        blame_counter[blamed_sha] += 1

        blames = []

        for blamed_sha, num_lines in blame_counter.items():
            blamed_commit, hunk = blamed_commits[blamed_sha]
            blames.append(Blame(hunk.patch.commit.sha, hunk.patch.old_file, hunk.patch.label, blamed_commit, num_lines))

        result_contributors = [SzzContributor(key, value[0], value[1]) for key, value in contributors.items()]
        log.info("Process %d give %d blames", rank, len(blames))
        Szz.__log_processing_time(self, "Process %d blame_commit elapsed time" % rank, start)

        return blames, result_contributors

    def __export_csv(self, blames_list: List[List[Blame]], contributors_list: List[List[SzzContributor]]):
        start = time.time()
        blame_metadata = []
        blamed_metadata = []

        for blame in list(itertools.chain.from_iterable(blames_list)):
            blamed = blame.blamed
            blame_metadata.append([self.__slug, blame.sha, blame.old_file, blame.label, blamed.sha, blame.num_lines])
            blamed_metadata.append(self.__commit_to_metadata(blamed))

        contributors = {contributor.id: contributor for contributor in
                        list(itertools.chain.from_iterable(contributors_list))}

        self.__contributors = {**self.__contributors, **contributors}  # merge dictionaries

        received_contributors = list(self.__contributors.values())

        received_contributors_metadata = [[self.__slug, contributor.id, contributor.name, contributor.email] for
                                          contributor in
                                          received_contributors]

        blame_df = pd.DataFrame(blame_metadata,
                                columns=["SLUG", "BUG_FIXING_COMMIT", "PATH", "TYPE", "BLAMED_COMMIT",
                                         "NUM_BLAMED_LINES"])
        blame_df.to_csv(os.path.join(self.__output_folder, self.__slug_unslashed + "_blames_commit.csv"), index=False)
        del blame_df

        blamed_df = pd.DataFrame(blamed_metadata,
                                 columns=self.__COMMIT_COLUMNS)
        blamed_df.to_csv(os.path.join(self.__output_folder, self.__slug_unslashed + "_blamed_commit.csv"), index=False)
        del blamed_df

        contributors_df = pd.DataFrame(received_contributors_metadata,
                                       columns=["SLUG", "CONTRIBUTOR_ID", "NAME", "EMAIL"])
        contributors_df.to_csv(os.path.join(self.__output_folder, self.__slug_unslashed + "_contributors.csv"),
                               index=False)

        Szz.__log_processing_time(self, "CSV export processing time", start)

    def __get_repo(self, copy: bool = False) -> pygit2.Repository:
        git_path = self.__repo_path
        if copy and rank > 0:
            git_path = "temp/" + self.__slug_unslashed + "/" + str(rank).zfill(Szz.__calculate_fill(self))
            log.info("Copying repo in path: %s" % git_path)
            utility.create_folder_if_not_exists(self.__repo_path, git_path)
        return pygit2.Repository(git_path)

    @staticmethod
    def __calculate_fill(self) -> int:
        fill = 2
        dividend = 10
        actual = mpisize / dividend
        while actual >= dividend:
            fill += 1
            dividend *= 10
        return fill

    def run(self):
        copy_path = True
        git_repo = self.__get_repo(copy_path)
        start = None

        if rank == 0:
            log.info("Executing SZZ in MPI mode: " + str(self.__mpi_enabled))
            log.info("Processing repository at path %s", self.__repo_path)
            start = time.time()
            start_hunk_fetch = time.time()
            szz_hunks = Szz.__fetch_hunks(self, git_repo)
            Szz.__log_processing_time(self, "Hunk fetching time", start_hunk_fetch)
        else:
            szz_hunks = None

        if self.__mpi_enabled:
            szz_hunks = comm.scatter(szz_hunks, root=0)
        else:
            szz_hunks = itertools.chain.from_iterable(szz_hunks)

        blamed_commits = []
        contributors = []
        if szz_hunks is not None:
            blamed_commits, contributors = self.__fetch_blamed_commits(szz_hunks, git_repo)

        received_data_blamed = [blamed_commits]
        received_data_contributors = [contributors]
        if self.__mpi_enabled:
            received_data_blamed = comm.gather(blamed_commits, root=0)
            received_data_contributors = comm.gather(contributors, root=0)

        if rank == 0:
            Szz.__log_processing_time(self, "Blamed commits. Total processing time", start)

            self.__export_csv(received_data_blamed, received_data_contributors)

            utility.delete_folder_if_exists("temp")


if __name__ == '__main__':
    help_message = 'Usage:\n SzzAlgorithm.py -r|--repo=<repo> -i|--issues=<issues_file> -o|--output=<output_folder> -l|--labels=<labels>'
    repo = None
    issues = None
    out_dir = None
    labels = ['fix', 'bug-fix', 'retain']

    try:
        if not sys.argv[1:]:
            raise getopt.GetoptError('No arguments passed from the command line. See help instructions.')
        opts, args = getopt.getopt(sys.argv[1:], "r:i:o:l:H", ["repo=", "issues=", "output=", "labels=", "help"])
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print(help_message)
                sys.exit(0)
            elif opt in ("-r", "--repo"):
                repo = arg
            elif opt in ("-i", "--issues"):
                issues = arg
            elif opt in ("-o", "--output"):
                out_dir = arg
            elif opt in ("-l", "--labels"):
                labels = arg
            else:
                assert False, "unhandled option"
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        print(help_message)
        sys.exit(1)

    try:
        szz = Szz(repo, issues, out_dir, labels)
        szz.run()
    except KeyboardInterrupt:
        log.error("Received Ctrl-C or another break signal. Exiting.")
