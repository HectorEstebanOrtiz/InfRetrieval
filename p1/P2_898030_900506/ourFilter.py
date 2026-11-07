from nltk.stem.snowball import SnowballStemmer
from whoosh.analysis import *

#Autores: Ciro Fustero Zumeta (NIP: 900506) y Héctor Esteban Ortiz (NIP: 898030)

#Clase que implementa nuestro filtro, esta en un fichero separado para que tanto search como index puedan usarla
class SnowballStemmerFilter(Filter):

    def __init__(self, lang='spanish'):
        #Usamos 'spanish' en vez de 'es' porque NLTK usa 'spanish' para el idioma español
        self.stemmer = SnowballStemmer(lang)

    def __call__(self, tokens):
        for t in tokens:
            #Modificamos el texto del token y lo devuelvemos con yield
            t.text = self.stemmer.stem(t.text)
            yield t

#Función que devuelve nuestro analizador personalizado
def custom_analyzer():
    return RegexTokenizer() | LowercaseFilter() | StopFilter(lang='es') | SnowballStemmerFilter(lang='spanish')