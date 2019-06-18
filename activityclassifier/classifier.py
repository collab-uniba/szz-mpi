'''
Created on Mar 19, 2017

@author: Bogdan Vasilescu
@author: Fisher Yu
'''

import os
import re

import yaml

RE_COMMENT = r'^([ \t]*(#|(\\\*)|(\*\*)|(//)|(/\*))|[ \t]*$)'
regex_comment = re.compile(RE_COMMENT)


class BasicFileTypeClassifier:
    # File type
    SRC = 0
    TEST = 1
    DOC = 2
    CFG_BUILD_OTHER = 3
    # Code change type in diff
    CG_CODE = 0
    CG_COMMENT = 1

    def __init__(self):
        self.rules = yaml.load(open(os.path.join(os.path.dirname(__file__), 'rules.yml')).read())

        # List of filename extensions from GitHub Linguist
        # https://github.com/github/linguist
        self.all_extensions = yaml.load(open(os.path.join(os.path.dirname(__file__), 'languages.yml')).read())
        popular = yaml.load(open(os.path.join(os.path.dirname(__file__), 'popular.yml')).read())
        self.extensions = {}
        for lang in popular:
            if lang in self.all_extensions:
                self.extensions[lang] = self.all_extensions[lang]

        self.reverse_extensions = {}
        for lang, d in self.extensions.items():
            for ext in d['extensions']:
                self.reverse_extensions.setdefault(ext, set([]))
                self.reverse_extensions[ext].add(lang)

    def labelDiffLine(self, diff_line):
        # NOTE_PT = r'^([ \t]*(#|(\\\*)|(\*\*)|(//)|(/\*))|[ \t]*$)'
        # pt = re.compile(NOTE_PT)
        match = regex_comment.match(diff_line)
        if match:
            return self.CG_COMMENT
        else:
            return self.CG_CODE

    def labelFile(self, file_name):
        base_name = os.path.basename(file_name)
        root_name, extension = os.path.splitext(base_name)

        # Skip .git folder
        if file_name.find("/.git/") != -1:
            return -1

        for signal in self.rules['Media']['path']:
            if file_name.find(signal) != -1:
                return self.DOC

        for signal in self.rules['Doc']['path']:
            if file_name.find(signal) != -1:
                return self.DOC

        if extension in self.rules['Doc']['extension']:
            return self.DOC

        if root_name in self.rules['Doc']['filename']:
            return self.DOC

        for signal in self.rules['Test']['path']:
            if file_name.find(signal) != -1:
                return self.TEST

        for signal in self.rules['Source']['path']:
            if file_name.find(signal) != -1:
                return self.SRC

        # SRC extensions          
        if extension in self.reverse_extensions:
            return self.SRC

        #         for signal in self.rules['Config']['path']:
        #             if file_name.find(signal) != -1:
        #                 return self.CFG_BUILD_OTHER
        #
        #         if root_name in self.rules['Config']['filename']:
        #             return self.CFG_BUILD_OTHER

        return self.CFG_BUILD_OTHER

    def guess_languages(self, files):
        files_data = dict()
        for file in files:
            found = False
            try:
                filename, ext = os.path.splitext(file)
            except:
                ext = False
            for lang in self.all_extensions:
                found = False
                try:
                    if not ext:
                        langs_info = self.all_extensions[lang]["filenames"]
                    else:
                        langs_info = self.all_extensions[lang]["extensions"]
                    for lang_info in langs_info:
                        if filename == lang_info or ext == lang_info:
                            files_data[file] = lang
                            found = True
                            break
                    if found:
                        break
                except:
                    continue
            if not found:
                files_data[file] = 'ambiguous'
        return files_data


if __name__ == "__main__":
    bc = BasicFileTypeClassifier()

    print('Popular languages:')
    print(sorted(bc.extensions.keys()))

    print('\nC++ extensions:')
    print(bc.extensions['C++']['extensions'])

    print('\nAmbiguous extensions:')
    for ext, langs in bc.reverse_extensions.items():
        if len(langs) > 1:
            print(ext, langs)

