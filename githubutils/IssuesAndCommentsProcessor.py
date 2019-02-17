import getopt
import socket
import sys
import threading
import traceback
import os
from queue import Queue

from github.GithubException import RateLimitExceededException
from github.GithubException import GithubException
from github.GithubException import BadCredentialsException
from github.GithubException import UnknownObjectException

from githubutils.BaseGithubThreadedExtractor import BaseGitHubThreadedExtractor
from githubutils.Tokens import Tokens
from githubutils.NoAvailableTokenException import NoAvailableTokenException

from loggingcfg import initialize_logger
import numpy as np
from numba import jit, prange
import pandas as pd
import loggingcfg

logger = loggingcfg.initialize_logger('SZZ-EXTRACTOR')


class IssuesAndCommentExtractor(BaseGitHubThreadedExtractor):
    __ISSUES_COLUMN_NAMES = ["SLUG", "ID", "NUMBER", "STATE", "CREATED_AT", "CLOSED_AT", "CREATED_BY_LOGIN",
                             "CLOSED_BY_LOGIN", "ASSIGNEE_LOGIN", "TITLE", "NUM_COMMENTS", "LABELS", "IS_PL"]

    __COMMENTS_COLUMN_NAMES = ["SLUG", "ISSUE_ID", "ISSUE_NUMBER", "COMMENT_ID", "BODY", "CREATED_AT", "UPDATED_AT",
                               "USER_LOGIN", "USER_ID"]

    @jit(parallel=True)
    def __to_df(self, issues, slug, g, issue_data, comment_data):
        repo = g.get_repo(slug)

        for i in prange(0, np.size(issues)):
            logger.debug("Looking for issue number %d", issues[i])
            issue = repo.get_issue(int(issues[i]))
            issue_data.append(self.__parse_issue(slug, issue))
            comment_data += self.__parse_comments(slug, issue)

    @jit
    def __parse_issue(self, slug, issue):
        issue_id = issue.id  # int
        issue_number = issue.number  # int
        state = issue.state  # string
        created_at = str(issue.created_at)  # datetime
        closed_at = str(issue.closed_at)  # datetime

        created_by = issue.user  # NamedUser
        created_by_login = None
        if created_by is not None:
            created_by_login = created_by.login

        closed_by = issue.closed_by  # NamedUser
        closed_by_login = None
        if closed_by is not None:
            closed_by_login = closed_by.login

        assignee = issue.assignee  # NamedUser
        assignee_login = None
        if assignee is not None:
            assignee_login = assignee.login

        title = issue.title.strip().replace("\n", "").replace("\r", "")  # string
        num_comments = issue.comments  # int
        labels = ';'.join([l.name for l in issue.labels])  # [Label]

        is_pl = issue.pull_request is not None

        return [slug, issue_id, issue_number, state, created_at, closed_at, created_by_login,
                closed_by_login, assignee_login, title, num_comments, labels, is_pl]

    def __parse_github_pages(self, issues, slug, g, issue_data=None, comment_data=None):
        if issue_data is None:
            issue_data = []
        if comment_data is None:
            comment_data = []
        logger.info("Issue detail to fetch: %d" % np.size(issues))
        try:
            self.__to_df(issues, slug, g, issue_data, comment_data)
        except socket.timeout or RateLimitExceededException as ste:
            logger.error("Socket timeout parsing issue", ste)
            df_issue, df_comments = self.__manage_parsing_exception(issues, slug, g, issue_data, comment_data)
        except RateLimitExceededException:
            logger.warn("Rate limit parsing issue")
            df_issue, df_comments = self.__manage_parsing_exception(issues, slug, g, issue_data, comment_data)
        except GithubException as exc:
            logger.warn("Generic exception", exc)
            df_issue, df_comments = self.__manage_parsing_exception(issues, slug, g, issue_data, comment_data)

        df_issue = pd.DataFrame(issue_data, columns=self.__ISSUES_COLUMN_NAMES)
        df_comments = pd.DataFrame(comment_data, columns=self.__COMMENTS_COLUMN_NAMES)

        return df_issue, df_comments

    def __manage_parsing_exception(self, issues, slug, g, issue_data, comment_data):
        pid = threading.get_ident()
        g = self._get_github_instance(pid, g)
        processed = np.array([x[2] for x in issue_data])
        logger.info("Processed: {0}".format(processed))
        remaining_issues = np.setdiff1d(issues, processed)
        logger.info("Issue size: {0}; remaining: {1}".format(np.size(issues), np.size(remaining_issues)))
        return self.__parse_github_pages(remaining_issues, slug, g, issue_data, comment_data)

    def issues_to_csv(self, slug: str, out_dir: str):
        df_issue: pd.DataFrame = None
        df_comments: pd.DataFrame = None
        pid = threading.get_ident()

        logger.info('[tid: {0}] Processing {1}'.format(pid, slug))

        try:
            g = self._get_github_instance(pid)
            repo = g.get_repo(slug)

            if repo:  # and repo.has_issues: sometimes returns False even when there are some
                issues = np.array([issue.number for issue in repo.get_issues(state="closed")], dtype=int)
                logger.info("Fetching {0} issues from repo {1}".format(np.size(issues), slug))
                df_issue, df_comments = self.__parse_github_pages(issues, slug, g)

        except BadCredentialsException:
            logger.warning("Repository %s seems to be private (raised 401 error)" % slug)
        except UnknownObjectException as e:
            logger.warning(e)
        except GithubException as ghe:
            logger.warning("Error for repository {0}, most likely there is no tab Issues in the repo".format(slug))
            traceback.print_exc(ghe)
        except NoAvailableTokenException as e:
            logger.fatal("No available tokens with sufficient valid rate limit.")
        except Exception as e:
            traceback.print_exc(e)
        finally:
            slug = slug.replace("/", "_")
            if df_issue is not None:
                df_issue.to_csv(os.path.join(out_dir, slug + "_issues.csv"), index=False)
            if df_comments is not None:
                df_comments.to_csv(os.path.join(out_dir, slug + "_comments.csv"), index=False)

    def __parse_comments(self, slug, issue):
        comments = []

        comments_pglist = issue.get_comments()
        for comment in comments_pglist:
            comment_id = comment.id
            body = comment.body.strip()
            created_at = comment.created_at
            updated_at = comment.updated_at
            user_login = comment.user.login
            user_gh_id = comment.user.id
            comments.append(
                [slug, issue.id, issue.number, comment_id, body, created_at, updated_at, user_login, user_gh_id])

        if issue.pull_request is not None:  # is an actual issue:  # is a PR
            pr = issue.repository.get_pull(issue.number)

            comments_pglist = pr.get_review_comments()
            for comment in comments_pglist:
                comment_id = comment.id
                created_at = comment.created_at
                updated_at = comment.updated_at
                body = comment.body.strip()
                try:
                    user_login = comment.user.login
                    user_gh_id = comment.user.id
                    comments.append(
                        [slug, pr.id, pr.number, comment_id, body, created_at, updated_at, user_login, user_gh_id])
                except AttributeError:
                    logger.error("Skipped comment {0} in project {1} with None as user".format(comment_id, slug))
                    continue

        return comments


if __name__ == '__main__':
    help_message = 'Usage:\n IssuesAndCommentsProcessor.py -s|--slug=<slug> -t|--tokens=<tokens> -o|--output=<output_dir>'
    slug = None
    out_dir = None
    tokens_file = None

    logger = initialize_logger(name="SZZ:ISSUES_COMMENTS")

    try:
        if not sys.argv[1:]:
            raise getopt.GetoptError('No arguments passed from the command line. See help instructions.')
        opts, args = getopt.getopt(sys.argv[1:], "s:t:o:H", ["slug=", "output=", "tokens", "help"])
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print(help_message)
                sys.exit(0)
            elif opt in ("-o", "--output"):
                out_dir = arg
            elif opt in ("-t", "--tokens"):
                tokens_file = arg
            elif opt in ("-s", "--slug"):
                slug = arg
            else:
                assert False, "unhandled option"
    except getopt.GetoptError as err:
        # print help information and exit:
        logger.error(err)  # will print something like "option -a not recognized"
        print(help_message)
        sys.exit(1)

    if tokens_file is not None:
        tokens = Tokens(tokens_file)
    else:
        tokens = Tokens()

    tokens_iter = tokens.iterator()
    tokens_queue = Queue()
    for token in tokens_iter:
        tokens_queue.put(token)
    tokens_map = dict()

    try:
        extractor = IssuesAndCommentExtractor(tokens, tokens_queue, tokens_map)
        logger.info("Beginning data extraction.")
        extractor.issues_to_csv(slug, out_dir)
        logger.info("Done.")
        exit(0)
    except KeyboardInterrupt:
        logger.error("Received Ctrl-C or another break signal. Exiting.")
