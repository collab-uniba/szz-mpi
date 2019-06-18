import csv
import sys


class CsvReader:
    """
    A CSV reader which will read rows from CSV file "f",
    which is encoded in the given encoding.
    """
    csv.field_size_limit(sys.maxsize)
    reader = None

    def __init__(self, csv_file, mode='r'):
        self.f = open(csv_file, mode, newline='\n', encoding='utf-8')
        self.reader = csv.reader(self.f, delimiter=';', dialect=csv.excel)

    def readrows(self):
        return self.reader

    def close(self):
        self.f.close()
