from szz.SzzCommit import SzzCommit


class SzzPatch:
    def __init__(self, old_file: str, label: int, commit: SzzCommit):
        self.__old_file = old_file
        self.__label = label
        self.__commit = commit

    @property
    def old_file(self):
        return self.__old_file

    @property
    def label(self):
        return self.__label

    @property
    def commit(self):
        return self.__commit

