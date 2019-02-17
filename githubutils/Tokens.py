import random
import os


class Tokens:
    def __init__(self, tk_path='github_tokens.txt'):
        self.tokens = []
        with open(os.path.join(os.getcwd(), tk_path), 'r') as tokens:
            for t in tokens:
                self.tokens.append(t.strip())
        random.shuffle(self.tokens)

    def length(self):
        return len(self.tokens)

    def iterator(self):
        return iter(self.tokens)
