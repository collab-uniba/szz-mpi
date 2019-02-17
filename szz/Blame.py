from szz.BlamedCommit import BlamedCommit


class Blame:
    def __init__(self, sha: str, old_file: str, label: int, blamed: BlamedCommit, num_lines: int):
        self.__sha = sha
        self.__old_file = old_file
        self.__label = label
        self.__blamed = blamed
        self.__num_lines = num_lines

    @property
    def sha(self):
        return self.__sha

    @property
    def old_file(self):
        return self.__old_file

    @property
    def label(self):
        return self.__label

    @property
    def blamed(self):
        return self.__blamed

    @property
    def num_lines(self):
        return self.__num_lines

