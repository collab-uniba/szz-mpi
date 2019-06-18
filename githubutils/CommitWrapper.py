import os
from datetime import datetime, timezone, timedelta
import pytz
import re
import logging

_RE_ISSUE_ID = re.compile(r'[^a-zA-Z0-9_#/](\#\d+)\b')
_RE2_ISSUE_ID = re.compile(r'\b(GH-\d+)\b')

logger = logging.getLogger('SZZ-COMMIT-WRAPPER')

class CommitWrapper:
    def __init__(self, commit):
        self.__commit = commit

    @property
    def sha(self):
        return self.__commit.hex

    @property
    def committer(self):
        return self.__commit.committer.name, self.__commit.committer.email

    @property
    def author(self):
        return self.__commit.author.name, self.__commit.author.email

    @property
    def committed_date(self):
        tzinfo = timezone(timedelta(minutes=self.__commit.committer.offset))
        dt = datetime.fromtimestamp(float(self.__commit.committer.time), tzinfo).astimezone(pytz.utc)
        return dt

    @property
    def authored_date(self):
        tzinfo = timezone(timedelta(minutes=self.__commit.author.offset))
        dt = datetime.fromtimestamp(float(self.__commit.author.time), tzinfo).astimezone(pytz.utc)
        return dt

    @property
    def message(self):
        return self.__commit.message

    @property
    def issue_ids(self):
        results = []
        for (line_num, line) in enumerate(self.message.split('\n')):
            matches = set([int(m[1:]) for m in re.findall(_RE_ISSUE_ID, line)])
            matches.update(set([int(m[3:]) for m in re.findall(_RE2_ISSUE_ID, line)]))
            if matches:
                results.append((line_num + 1, sorted(matches)))
        return results

    @property
    def parents(self):
        return self.__commit.parents

    def diff(self, repo):
        return repo.diff(self.__commit.parents[0], self.__commit, context_lines=0)

    @staticmethod
    def get_src_changes(basic_classifier, diff):
        src_loc_added = 0
        src_loc_deleted = 0
        num_src_files_touched = 0
        src_files = []
        all_files = []
        for patch in diff:
            if not patch.delta.is_binary:
                """
                unlike the blame part, here we look at the new files of the patch
                as they contain both the old files that are being modified, plus
                the new ones, just created from scratch
                """
                f = patch.delta.new_file
                all_files.append(os.path.basename(f.path))
                if basic_classifier.labelFile(f.path) != basic_classifier.DOC:  # not a doc file
                    num_src_files_touched += 1
                    src_files.append(os.path.basename(f.path))
                    for hunk in patch.hunks:
                        for hl in hunk.lines:
                            if hl.origin == '-':
                                src_loc_deleted += 1
                            elif hl.origin == '+':
                                src_loc_added += 1
                else:
                    logger.debug("Skipped doc file %s" % f.path)
            else:
                logger.debug("Skipped binary delta.")
        if src_files:
            src_files = ';'.join(src_files)
        else:
            src_files = ''
        if all_files:
            all_files = ';'.join(all_files)
        else:
            all_files = ''
        return all_files, src_files, num_src_files_touched, src_loc_added, src_loc_deleted
