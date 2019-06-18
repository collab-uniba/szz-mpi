class SzzCommit:
    def __init__(self, sha: str, sha_parent: str):
        self.__sha = sha
        self.__sha_parent = sha_parent

    @property
    def sha(self):
        return self.__sha

    @property
    def sha_parent(self):
        return self.__sha_parent

