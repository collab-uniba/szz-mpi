import datetime
import threading
from githubutils.GithubWrapper import GithubWrapper
from githubutils.NoAvailableTokenException import NoAvailableTokenException

import wrapt

import loggingcfg

logger = loggingcfg.initialize_logger('SZZ')


# see http://wrapt.readthedocs.io/en/latest/examples.html#thread-synchronization
@wrapt.decorator
def synchronized(wrapped, instance, args, kwargs):
    # Use the instance as the context if function was bound.

    if instance is not None:
        context = vars(instance)
    else:
        context = vars(wrapped)

    # Retrieve the lock for the specific context.
    lock = context.get('_synchronized_lock', None)

    if lock is None:
        # There was no lock yet associated with the function so we
        # create one and associate it with the wrapped function.
        # We use ``dict.setdefault()`` as a means of ensuring that
        # only one thread gets to set the lock if multiple threads
        # do this at the same time. This may mean redundant lock
        # instances will get thrown away if there is a race to set
        # it, but all threads would still get back the same one lock.

        lock = context.setdefault('_synchronized_lock',
                                  threading.RLock())

    with lock:
        return wrapped(*args, **kwargs)


class BaseGitHubThreadedExtractor:
    tokens = None
    tokens_queue = None
    tokens_map = None
    tokens_deplated = None

    def __init__(self, _tokens, t_queue, t_map):
        self.tokens = _tokens
        self.tokens_queue = t_queue
        self.tokens_map = t_map
        self.tokens_deplated = dict()

    def initialize(self):
        pass

    def __reserve_token(self, tid):
        self.__check_renewed()
        token = self.tokens_queue.get()

        if token is None:
            # If there are no available tokens, raise exception.
            raise NoAvailableTokenException

        if self.tokens_deplated.get(token) is not None:
            #If the token is deplated, give me another one.
            token = self.__reserve_token(tid)

        self.tokens_map[tid] = token
        return token

    def __release_token(self, tid, token):
        if self.tokens_map[tid] == token:
            self.tokens_queue.put(token)
            self.tokens_map.pop(tid)

    def __check_renewed(self):
        now = datetime.datetime.now()
        for token, availability in self.tokens_deplated.copy().items():
            if now >= availability:
                self.tokens_queue.put(token)
                del self.tokens_deplated[token]


    @synchronized
    def _get_github_instance(self, pid, g=None):
        github: GithubWrapper = g

        if g is None:
            github = GithubWrapper(self.__reserve_token(pid))

        while not github.get_rate_limit().core.remaining > 5:
            available = datetime.datetime.fromtimestamp(github.rate_limiting_resettime)
            self.tokens_deplated[github.access_token] = available
            self.__release_token(pid, github.access_token)
            github = GithubWrapper(self.__reserve_token(pid))
            logger.info("[tid: {0}] Process renewed.".format(pid))

        return github


if __name__ == '__main__':
    from githubutils.Tokens import Tokens

    tokens = Tokens('../github_tokens.txt').iterator()
    print("Token\t\t\t\t\t\t\t\t\t\tRemaining")
    for t in tokens:
        g = GithubWrapper(t)
        remaining = g.get_rate_limit()
        print("{0}\t{1}".format(t, remaining))
