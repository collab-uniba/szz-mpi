from szz.SzzPatch import SzzPatch


class SzzHunk:
    def __init__(self, old_lines: int, old_start: int, patch: SzzPatch, line_labels):
        self.__old_lines = old_lines
        self.__old_start = old_start
        self.__patch = patch
        self.__line_labels = line_labels

    @property
    def old_lines(self):
        return self.__old_lines

    @property
    def old_start(self):
        return self.__old_start

    @property
    def patch(self):
        return self.__patch
    
    @property
    def line_labels(self):
        return self.__line_labels
