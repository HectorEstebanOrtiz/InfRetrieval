from nltk.stem.snowball import SnowballStemmer
from whoosh.analysis import *


class SnowballStemmerFilter(Filter):

    def __init__(self, lang='spanish'):
        # NLTK utiliza el nombre completo del idioma ('spanish')
        self.stemmer = SnowballStemmer(lang)

    def __call__(self, tokens):
        for t in tokens:
            # Modifica el texto del token y lo devuelve con yield
            t.text = self.stemmer.stem(t.text)
            yield t

def custom_analyzer():
    return RegexTokenizer() | LowercaseFilter() | StopFilter(lang='es') | SnowballStemmerFilter(lang='spanish')