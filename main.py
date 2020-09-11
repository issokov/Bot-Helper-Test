import json
import re
from operator import itemgetter

import nltk
import string
import requests

from collections import Counter
from nltk.corpus import stopwords


class CommitMessageStats:
    whitespace = "\r\n\t"
    punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""

    def __init__(self, config_file_name: str):
        self.config = json.load(open(config_file_name, "rb"))
        self.raw_json_data = None
        self.prepared_text = None
        self.tokens = None
        self.token_freq = Counter()
        self.result = None

    def collect_commits(self):
        headers = {'ACCEPT': 'application/vnd.github.v3+json'}
        owner = self.config.get('organisation', None)
        repo = self.config.get('repository', None)
        queries = {
            "sha": self.config.get('branch', 'master'),
            "per_page": min(100, max(0, int(self.config.get('commits_count'))))
        }
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        self.raw_json_data = requests.get(url, params=queries, headers=headers).json()

    def is_data_correct(self) -> bool:
        if not self.raw_json_data:
            raise RuntimeError('Collect the data before use is_data_correct().')
        if 'message' in self.raw_json_data and 'documentation_url' in self.raw_json_data:
            raise RuntimeError(
                f"API interaction error: {self.raw_json_data['message']}.\n"
                "This may be the wrong organisation or repository name.\n"
                f"Please check {self.raw_json_data['documentation_url']}")
        return 'message' not in self.raw_json_data and 'documentation_url' not in self.raw_json_data

    def prepare_text(self):
        self.prepared_text = ' '.join([commit['commit']['message'] for commit in self.raw_json_data])
        if self.config.get('make_tokens_lower', True):
            self.prepared_text = self.prepared_text.lower()
        if self.config.get('drop_punctuation', True):
            self.prepared_text = self.prepared_text.translate(str.maketrans('', '', string.punctuation))
        self.prepared_text = self.prepared_text.translate(str.maketrans('', '', self.whitespace))
        self.prepared_text = re.sub(' +', ' ', self.prepared_text)  # remove the extra spaces

    def calc_frequencies(self):
        self.tokens = self.prepared_text.split(' ')
        if self.config.get('drop_stop_words', True):
            nltk.download('stopwords')
            eng_stopwords = stopwords.words('english')
            self.tokens = filter(lambda token: token.lower() not in eng_stopwords, self.tokens)
        self.token_freq.update(self.tokens)

    def run(self):
        self.collect_commits()
        if self.is_data_correct():
            self.prepare_text()
            self.calc_frequencies()
            sorted_tokens = sorted(self.token_freq.items(), key=itemgetter(1), reverse=True)
            self.result = '\n'.join([f"{token} {count}" for token, count in sorted_tokens])
            print(self.result)

    def dump_results(self, path_to_dump = None):
        path_to_dump = path_to_dump if path_to_dump else self.config.get('dump_file_name', 'frequencies.txt')
        with open(path_to_dump, "w") as file:
            file.write(self.result)


if __name__ == "__main__":
    cms = CommitMessageStats('config.json')
    cms.run()
    cms.dump_results()
