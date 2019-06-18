import pandas as pd
from dateutil import parser
import datetime
from typing import Dict


class Issue:
    def __init__(self, number: int, title: str, created_at: str, closed_at: str, labels: str, is_pl: bool):
        self.__number = number
        self.__title = title
        self.__labels = None if labels is None or labels == '' else labels.split(";")
        self.__is_pl = is_pl
        if created_at is not None and created_at != 'None':
            st = parser.parse(created_at)
            self.__created_at = datetime.datetime(st.year, st.month, st.day, st.hour,
                                                  st.minute, st.second)
        else:
            self.__created_at = None

        if closed_at is not None and closed_at != 'None':
            st = parser.parse(closed_at)
            self.__closed_at = datetime.datetime(st.year, st.month, st.day, st.hour,
                                                 st.minute, st.second)
        else:
            self.__closed_at = None

    @property
    def number(self):
        return self.__number

    @property
    def title(self):
        return self.__title

    @property
    def created_at(self):
        return self.__created_at

    @property
    def closed_at(self):
        return self.__closed_at

    @property
    def labels(self):
        return self.__labels

    @property
    def is_pl(self):
        return self.__is_pl

    def __repr__(self):
        return "Issue(number: {0}, title: {1}, created_at: {2}, closed_at: {3}, labels: {4}, is_pl: {5})".format(
            self.__number, self.__title, self.__created_at, self.__closed_at, self.__labels, self.__is_pl)


def from_csv(csv_path: str) -> Dict[int, Issue]:
    issue_dict = dict()
    df = pd.read_csv(csv_path, index_col=False, dtype={'NUMBER': int, 'LABELS': str}, na_filter=False)
    for row in df.itertuples():
        issue = Issue(getattr(row, 'NUMBER'), getattr(row, 'TITLE'), getattr(row, 'CREATED_AT'),
                      getattr(row, 'CLOSED_AT'), getattr(row, 'LABELS'), getattr(row, 'IS_PL'))
        issue_dict[issue.number] = issue

    return issue_dict


def main():
    print(from_csv('test.csv'))


if __name__ == '__main__':
    main()
