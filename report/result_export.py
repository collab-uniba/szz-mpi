import datetime
import logging
import os
import pickle
import sys
import time
from time import strftime
from utils import utility
import pandas
import getopt

import loggingcfg
from activityclassifier import BasicFileTypeClassifier

logger = loggingcfg.initialize_logger(name='RESULT-EXPORT', console_level=logging.INFO)


def replace_alias(aliases, author_id):
    return aliases[author_id]


def parse_timestamp(date, time_unit):
    gb = None
    date_d1 = time.strptime('1990-01-01', "%Y-%m-%d")
    date_d2 = time.strptime(str(date).split(' ')[0], "%Y-%m-%d")

    year_d1 = int((strftime("%Y", date_d1)))
    year_d2 = int((strftime("%Y", date_d2)))

    if time_unit == 'week':
        week_d2 = int((strftime("%U", date_d2)))
        gb = ((year_d2 - year_d1) * 52) + week_d2
    elif time_unit == 'month':
        month_d2 = int((strftime("%m", date_d2)))
        gb = ((year_d2 - year_d1) * 12) + month_d2
    return gb


def daily_data_per_language(commits, lang, basic_classifier):
    src_files_for_lang = []
    num_src_file_touches_for_lang = 0
    for commit in commits:
        for file in commit[3].split(','):  # src files in the commit
            gl = basic_classifier.guess_languages([file])
            if lang == gl[file]:
                src_files_for_lang.append(file)
                num_src_file_touches_for_lang += 1

    num_src_files_touched_for_lang = len(set(src_files_for_lang))

    return num_src_file_touches_for_lang, num_src_files_touched_for_lang


def daily_data_per_project(commits_set):
    all_files = []
    src_files = []
    num_files_touches_per_day = 0
    num_src_files_touches_per_day = 0
    # num_files_touched_per_day = 0
    # num_src_files_touched_per_day = 0
    for commit in commits_set:
        if commit[3] != '':
            commit_files = commit[3].split(',')  # any files touched in commit
            all_files = all_files + commit_files
            num_files_touches_per_day += len(commit_files)
        if commit[4] != '':
            src_commit_files = commit[4].split(',')  # src files touched in commit
            src_files = src_files + src_commit_files
            num_src_files_touches_per_day += len(src_commit_files)
            # beware!
            # num_files_touched_per_day += commit[9]  # num_files_touched in commit != from  num_files_touched_per_day
            # num_src_files_touched_per_day += commit[10]  # num_src_files_touched in commit != from num_src_files_touched_per_day

    num_files_touched_per_day = len(set(all_files))
    num_src_files_touched_per_day = len(set(src_files))

    return num_files_touches_per_day, num_src_files_touches_per_day, num_files_touched_per_day, \
           num_src_files_touched_per_day


def __export(input_folder: str, out_folder: str, aliases: dict, basic_classifier):
    # prj_outfile = argv[0]
    # lang_outfile = argv[1]

    logger.info("Retrieving blamed shas of bug-inducing commits (to src files only).")
    blames_df = utility.read_from_folder(input_folder, "*_blames_commit.csv", usecols=["SLUG", "BUG_FIXING_COMMIT", "BLAMED_COMMIT", "TYPE", "NUM_BLAMED_LINES"])
    blamed_df = utility.read_from_folder(input_folder, "*_blamed_commit.csv", usecols=["SLUG", "SHA", "AUTHOR_ID"])
    issue_links_df = utility.read_from_folder(input_folder, "*_issue_links.csv", usecols=["SLUG","COMMIT_SHA","ISSUE_NUMBER"])
    contributors_df = utility.read_from_folder(input_folder, "*_contributors.csv")
    commit_files_df = utility.read_from_folder(input_folder, "*_commit_files.csv")

    blamed_commits = blames_df[blames_df.TYPE != BasicFileTypeClassifier.DOC].merge(blamed_df, left_on=['SLUG', 'BLAMED_COMMIT'], right_on=['SLUG', 'SHA'], how='inner').merge(issue_links_df, left_on=["SLUG", "BUG_FIXING_COMMIT"], right_on=["SLUG", "COMMIT_SHA"])[['SLUG', 'BUG_FIXING_COMMIT', 'BLAMED_COMMIT', 'AUTHOR_ID', 'ISSUE_NUMBER', 'NUM_BLAMED_LINES']]

    # blamed_commits = session.query(Blame.sha, Blame.blamed_sha, Repo.slug, Blame.repo_id, Commit.author_id,
    #                                IssueLink.issue_number, Blame.num_blamed_lines) \
    #     .filter(Commit.sha == Blame.blamed_sha,
    #             Blame.sha == IssueLink.sha,
    #             Blame.type != BasicFileTypeClassifier.DOC,
    #             Blame.repo_id == Repo.id).all()

    logger.info("Retrieving the list of distinct authors of blamed commits (taking care of aliases too).")
    bugs_induced_per_sha = dict()
    for bc in blamed_commits.itertuples():
        sha = getattr(bc, "BUG_FIXING_COMMIT")
        blamed_sha = getattr(bc, "BLAMED_COMMIT")
        issue_number = getattr(bc, "ISSUE_NUMBER")
        slug = getattr(bc, "SLUG")
        author_id = getattr(bc, "AUTHOR_ID")
        logger.debug("Retrieving developer who created commit with sha: %s" % blamed_sha)
        u = contributors_df[(contributors_df.SLUG == slug) & (contributors_df.CONTRIBUTOR_ID == author_id)].head(1)

        if u.empty:
            logging.error("No user with id {0} found for repo {1}".format(author_id, slug))
            continue

        if u['EMAIL'].iloc[0] == 'noreply@github.com' and u['NAME'].iloc[0] == 'github':
            logger.info("Skipped user %s whose name and email values are GitHub's defaults." % u.ID)
            continue

        aliased_uid = replace_alias(aliases, u['CONTRIBUTOR_ID'].iloc[0])

        if (aliased_uid, blamed_sha, slug) in bugs_induced_per_sha:
            bug_fixing_commits = bugs_induced_per_sha[(aliased_uid, blamed_sha, slug)]
        else:
            bug_fixing_commits = dict()

        if issue_number in bug_fixing_commits:
            bug_fixes = bug_fixing_commits[issue_number]
        else:
            bug_fixes = list()
        bug_fixes.append(sha)
        bug_fixing_commits[issue_number] = bug_fixes
        bugs_induced_per_sha[(aliased_uid, blamed_sha, slug)] = bug_fixing_commits

    logger.info("Parsing commits.")
    df_commits = utility.read_from_folder(input_folder, "*_commits.csv")
    commits_per_user = dict()
    dates = set()  # set of all commit dates
    langs = set()  # set of all progr languages used in commits
    repos = set()  # set of all repos

    #SLUG,SHA,TIMESTAMP,AUTHOR_ID,COMMITTER_ID,MESSAGE,NUM_PARENTS,NUM_ADDITIONS,NUM_DELETIONS,NUM_FILES_CHANGED,FILES,SRC_LOC_ADDED,SRC_LOC_DELETED,NUM_SRC_FILES_TOUCHED,SRC_FILES

    for commit in df_commits.itertuples():
        author_id = getattr(commit, "AUTHOR_ID")
        slug = getattr(commit, "SLUG")
        logger.debug("Parsing user %s from repo %s." % (author_id, slug))
        aliased_uid = replace_alias(aliases, author_id)
        logger.debug("Replaced %s with alias %s." % (author_id, aliased_uid))

        if aliased_uid in commits_per_user:
            commits_per_user_project, commits_per_user_language = commits_per_user[aliased_uid]
        else:
            commits_per_user_project = list()
            commits_per_user_language = list()

        repos.add(slug)

        # per-project metadata
        # repo = session.query(Repo.slug).filter_by(id=commit.repo_id).one()
        # repo = slugToFolderName(repo.slug)  # slug_transform(repo.slug)
        # repos.add(repo)
        y_m_d = str(getattr(commit, "TIMESTAMP")).split(' ')[0]
        dates.add(y_m_d)

        loc_added = getattr(commit, "NUM_ADDITIONS")
        loc_deleted = getattr(commit, "NUM_DELETIONS")
        num_files_touched = getattr(commit, "NUM_FILES_CHANGED")
        files = getattr(commit, "FILES")

        src_loc_added = getattr(commit, "SRC_LOC_ADDED")
        src_loc_deleted = getattr(commit, "SRC_LOC_DELETED")
        num_src_files_touched = getattr(commit, "NUM_SRC_FILES_TOUCHED")
        src_files = getattr(commit, "SRC_FILES")
        sha = getattr(commit, "SHA")

        issues = set()
        bug_fixes_per_issue = list()  # duplicates issues, only for debugging purposes
        if (aliased_uid, sha, slug) in bugs_induced_per_sha:  # if it's a blamed sha, how many times
            bug_fixing_commits = bugs_induced_per_sha[(aliased_uid, sha, slug)]
            for issue_no in bug_fixing_commits.keys():
                issues.add(str(issue_no))
            for commits in bug_fixing_commits.values():
                bug_fixes_per_issue += [c for c in commits]
        issues = ';'.join(list(issues))
        bug_fixes_per_issue = ';'.join(bug_fixes_per_issue)

        c_metadata_project = (aliased_uid, slug, y_m_d, files, src_files, loc_added, src_loc_added, loc_deleted,
                              src_loc_deleted, num_files_touched, num_src_files_touched, sha, issues,
                              bug_fixes_per_issue)
        commits_per_user_project.append(c_metadata_project)

        # per-language metadata
        if src_files:
            src_files = src_files.split(';')
            for file in src_files:
                commit_file = commit_files_df[(commit_files_df.SLUG == slug) & (commit_files_df.SHA == sha) & (commit_files_df.COMMIT_FILE == file)].head(1)
                if commit_file.empty:
                    logger.error("%s: no file %s found in commit %s" % (slug, file, sha))
                    continue
                try:
                    assert (BasicFileTypeClassifier.DOC != commit_file['LANG'].iloc[0]), "Language mismatch error"
                except AssertionError:
                    logger.error("%s: non-source file %s, skipping." % (slug, file))
                    continue

                loc_added = commit_file['LOC_INS'].iloc[0]
                loc_deleted = commit_file['LOC_DEL'].iloc[0]
                lang_info = basic_classifier.guess_languages([file])
                lang = list(lang_info.values())[0]
                langs.add(lang)
                c_metadata_language = (aliased_uid, lang, y_m_d, file, loc_added, loc_deleted, sha)
                commits_per_user_language.append(c_metadata_language)

        commits_per_user[aliased_uid] = (commits_per_user_project, commits_per_user_language)

    logger.info("Sorting the list of distinct dates from blamed commits.")
    distinct_dates = sorted(dates, key=lambda x: datetime.datetime.strptime(x, '%Y-%m-%d'))

    logger.info("Sorting the list of distinct repo slugs from the commits.")
    distinct_projects = sorted(repos)

    logger.info("Sorting the list of distinct source languages used for commits.")
    distinct_languages = sorted(langs)

    prj_rows = []
    lang_rows = []
    logger.info("Performing project and language aggregation of blamed-commits daily metadata per user.")
    j = 0
    for y_m_d in distinct_dates:
        j += 1
        logger.info("Aggregating result by day {0} ({1}/{2})".format(y_m_d, j, len(distinct_dates)))
        for aliased_uid, (user_commits_project, user_commits_languages) in commits_per_user.items():
            # project aggregation
            i = 0
            for project in distinct_projects:
                i += 1
                logger.debug("Aggregating by project %s/%s" % (i, len(distinct_projects)))
                daily_commits_per_project = []
                loc_added = 0
                loc_deleted = 0
                src_loc_added = 0
                src_loc_deleted = 0
                bugs = []
                bug_inducing_commits = 0
                for ucp in user_commits_project:
                    if y_m_d == ucp[2] and project == ucp[1]:
                        daily_commits_per_project.append(ucp)
                if daily_commits_per_project:
                    d_num_file_touches, d_num_src_file_touches, d_num_files_touched, d_num_src_files_touched = \
                        daily_data_per_project(set(daily_commits_per_project))
                    for commit_daily in daily_commits_per_project:
                        loc_added += commit_daily[5]
                        src_loc_added += commit_daily[6]
                        loc_deleted += commit_daily[7]
                        src_loc_deleted += commit_daily[8]
                        if commit_daily[12] != '':
                            bugs += commit_daily[12].split(',')
                            bug_inducing_commits += 1
                    bugs = len(set(bugs))
                    prj_rows.append([aliased_uid, project, y_m_d, len(daily_commits_per_project), d_num_file_touches,
                                     d_num_src_file_touches, d_num_files_touched, d_num_src_files_touched, loc_added,
                                     src_loc_added, loc_deleted, src_loc_deleted, bugs, bug_inducing_commits])

            # language aggregation
            i = 0
            for lang in distinct_languages:
                i += 1
                logger.debug("Aggregating by language %s/%s" % (i, len(distinct_languages)))
                daily_commits_per_language = []
                src_loc_added = 0
                src_loc_deleted = 0

                for ucl in user_commits_languages:
                    if y_m_d == ucl[2] and lang == ucl[1]:
                        daily_commits_per_language.append(ucl)
                if daily_commits_per_language:
                    num_src_file_touches, num_src_files_touched = daily_data_per_language(daily_commits_per_language,
                                                                                          lang, basic_classifier)
                    for commit_daily in daily_commits_per_language:
                        src_loc_added += int(commit_daily[4])
                        src_loc_deleted += int(commit_daily[5])
                    lang_rows.append(
                        [aliased_uid, lang, y_m_d, len(daily_commits_per_language), num_src_file_touches,
                         num_src_files_touched, src_loc_added, src_loc_deleted])

    logger.info("Writing to files.")
    prj_outfile = os.path.join(out_folder, "user_project_date_totalcommits.csv")
    """
    - user_project_date_totalcommits.csv
        user_id;project;date;num_commits;num_file_touches;num_src_file_touches;num_files_touched;num_src_files_touched;loc_added;src_loc_added;loc_deleted;src_loc_deleted
        2;bbatsov_ruby-style-guide;2011-09-27;1;1;0;1;0;2;;2;

    """
    prj_header = ['user_id', 'project', 'day', 'num_commits', 'num_file_touches', 'num_src_file_touches',
                  'num_files_touched', 'num_src_files_touched', 'loc_added', 'src_loc_added', 'loc_deleted',
                  'src_loc_deleted', 'num_bugs_induced', 'num_bug_inducing_commits']
    prj_df = pandas.DataFrame(prj_rows, columns=prj_header)
    prj_df.to_csv(prj_outfile, index=False)
    logger.info("Done writing %s." % prj_outfile)

    lang_outfile = os.path.join(out_folder, "user_language_date_totalcommits.csv")
    """
    - user_language_date_totalcommits.csv
    #user_id;language;date;num_commits;num_file_touches;num_files_touched;loc_added;loc_deleted
    #2;c;2013-09-29;1;1;1;8;0
    """
    lang_header = ['user_id', 'language', 'day', 'num_commits', 'num_src_file_touches', 'num_src_files_touched',
                   'src_loc_added', 'src_loc_deleted']
    lang_df = pandas.DataFrame(lang_rows, columns=lang_header)
    lang_df.to_csv(lang_outfile, index=False)
    logger.info("Done writing %s." % lang_outfile)


if __name__ == '__main__':
    help_message = 'Usage:\n result_export.py -i|--input=<input_dir> -o|--output=<output_dir>'
    input_dir = None
    out_dir = None

    try:
        if not sys.argv[1:]:
            raise getopt.GetoptError('No arguments passed from the command line. See help instructions.')
        opts, args = getopt.getopt(sys.argv[1:], "i:o:H", ["input=", "output=", "help"])
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print(help_message)
                sys.exit(0)
            elif opt in ("-i", "--input"):
                input_dir = arg
            elif opt in ("-o", "--output"):
                out_dir = arg
            else:
                assert False, "unhandled option"
    except getopt.GetoptError as err:
        # print help information and exit:
        logger.error(err)  # will print something like "option -a not recognized"
        print(help_message)
        sys.exit(1)

    try:
        aliases = os.path.join(input_dir, "idm/dict/aliasMap.dict")
        alias_map = {}
        with open(aliases, "rb") as f:
            unpickler = pickle.Unpickler(f)
            alias_map = unpickler.load()
        __export(input_dir, out_dir, alias_map, BasicFileTypeClassifier())
        logger.info("Done")
    except KeyboardInterrupt:
        logger.error("Received Ctrl-C or another break signal. Exiting.")
