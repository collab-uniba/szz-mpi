from github import Github


class GithubWrapper(Github):

    def __init__(self, access_token: str, per_page: int = 100):
        super().__init__(access_token, per_page=per_page)
        self.__access_token = access_token

    @property
    def access_token(self):
        return self.__access_token

