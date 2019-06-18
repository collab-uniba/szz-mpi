class Commit:
    def __init__(self, sha: str, timestamp, author_id: str, committer_id: str, message: str, num_parents: int, num_additions: int, num_deletions: int, num_files_changed: int, files: int, src_loc_added: int, src_loc_deleted: int, num_src_files_touched: int, src_files: str):
        self.__sha = sha
        self.__timestamp = timestamp
        self.__author_id = author_id
        self.__committer_id = committer_id
        self.__message = message
        self.__num_parents = num_parents
        self.__num_additions = num_additions
        self.__num_deletions = num_deletions
        self.__num_files_changed = num_files_changed
        self.__files = files # semi-colon list of file names
        self.__src_loc_added = src_loc_added
        self.__src_loc_deleted = src_loc_deleted
        self.__num_src_files_touched = num_src_files_touched
        self.__src_files = src_files # semi-colon list of file names

    @property
    def sha(self):
        return self.__sha

    @property
    def timestamp(self):
        return self.__timestamp

    @property
    def author_id(self):
        return self.__author_id

    @property
    def committer_id(self):
        return self.__committer_id

    @property
    def message(self):
        return self.__message

    @property
    def num_parents(self):
        return self.__num_parents

    @property
    def num_additions(self):
        return self.__num_additions

    @property
    def num_deletions(self):
        return self.__num_deletions

    @property
    def num_files_changed(self):
        return self.__num_files_changed

    @property
    def src_loc_added(self):
        return self.__src_loc_added

    @property
    def src_loc_deleted(self):
        return self.__src_loc_deleted

    @property
    def num_src_files_touched(self):
        return self.__num_src_files_touched

    @property
    def src_files(self):
        return self.__src_files

    @property
    def files(self):
        return self.__files

