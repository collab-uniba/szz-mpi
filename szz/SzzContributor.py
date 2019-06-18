class SzzContributor:
    def __init__(self, id: str, name: str, email: str):
        self.__id = id
        self.__name = name
        self.__email = email

    @property
    def id(self):
        return self.__id

    @property
    def name(self):
        return self.__name

    @property
    def email(self):
        return self.__email

