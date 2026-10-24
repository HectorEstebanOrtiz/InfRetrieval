"""
search.py
Author: Javier Nogueras Iso
Last update: 2024-09-07

Program to search a free text query on a previously created inverted index.
This program is based on the whoosh library. See https://pypi.org/project/Whoosh/ .
Usage: python search.py -index <index folder>
"""

#Autores: Ciro Fustero Zumeta (NIP: 900506) y Héctor Esteban Ortiz (NIP: 898030)

import sys

from whoosh.qparser import QueryParser
from whoosh.qparser import MultifieldParser
from whoosh.qparser import OrGroup
from whoosh import scoring
from ourFilter import *
import whoosh.index as index
from whoosh.query import And, NumericRange, Or
import re
import spacy

class MySearcher:
    def __init__(self, index_folder, model_type = 'tfidf'):
        ix = index.open_dir(index_folder)
        if model_type == 'tfidf':
            # Apply a vector retrieval model as default
            self.searcher = ix.searcher(weighting=scoring.TF_IDF())
        else:
            # Apply the probabilistic BM25F model, the default model in searcher method
            self.searcher = ix.searcher()
        #Añadimos los campos nuevos del schema al parser
        self.parser = MultifieldParser(["content", "title", "subject", "description", "date", "creator", "contributor", "publisher", "identifier", "west", "east", "south", "north"], ix.schema, group = OrGroup)

    def search(self, query_text, query_idx, output, show_info=False):
        spatial_query = None
        match = re.search(r'spatial:([-\d\.]+),([-\d\.]+),([-\d\.]+),([-\d\.]+)', query_text)
        if match:
            west, east, south, north = map(float, match.groups())
            westRangeQuery =  NumericRange ("west", start = None , end = east )
            eastRangeQuery =  NumericRange ("east", start = west , end = None )
            southRangeQuery =  NumericRange ("south", start = None , end = north )
            northRangeQuery =  NumericRange ("north", start = south , end = None )
            spatial_query = And([westRangeQuery, eastRangeQuery, southRangeQuery, northRangeQuery])
            query_text = query_text[:match.start()] + query_text[match.end():]
        cleaned_query_text = query_text.strip()
        query = self.parser.parse(cleaned_query_text) if cleaned_query_text else None
        if query and spatial_query:
            final_query = Or([query, spatial_query])
        elif spatial_query:
            final_query = spatial_query
        elif query:
            final_query = query
        else:
            print("Consulta vacía.")
            return
        results = self.searcher.search(final_query, limit = None)
        print(f'Query: {final_query}')
        if output is not None:
                with open(output, 'a', encoding='utf-8') as f:
                    for i, result in enumerate(results[:100], start=1):
                        print(f'{query_idx}     {result.get("identifier")}  Similarity score: {result.score}', file=f)
                        if show_info:
                            print(f'   Last Date Modified: {result.get("modtime")}')
                print('Check output file for results')
        else:
            for i, result in enumerate(results, start=1):
                print(f'{i} - File path: {result.get("path")}, Similarity score: {result.score}')
                if show_info:
                    print(f'   Last Date Modified: {result.get("modtime")}')

def sacarFechas(text):
    patrones = [
        #"entre [el año] X y [el año] Y"
        r'\bentre\s+(?:el\s+año\s+)?(\d{4})\s+y\s+(?:el\s+año\s+)?(\d{4})\b',
        
        #"desde/de [el [año]] X hasta [el [año]] Y"
        # CORRECCIÓN 2: Se añade ?: en de|desde para que no lo capture
        r'\b(?:de|desde)\s+(?:el(?:\s+año)?\s+)?(\d{4})\s+hasta\s+(?:el(?:\s+año)?\s+)?(\d{4})\b',
        
        #de/del/desde X al Y
        r'\b(?:de|del|desde)\s+(\d{4})\s+(?:a|al)\s+(\d{4})\b',
        
        #en el año X/ del año X/ año X (fechas únicas)
        r'\b(?:en\s+el\s+año|del\s+año|año|en)\s+(\d{4})\b'
    ]

    for patron in patrones:
        match = re.search(patron, text, re.IGNORECASE)
        if match:
            grupos = match.groups()
            
            # Inicializamos a None por si acaso
            fecha_fin = None 
            
            if len(grupos) >= 2 and grupos[1] is not None:
                fecha_inicio = int(grupos[0])
                fecha_fin = int(grupos[1])
            else:
                fecha_inicio = int(grupos[0])
                
            return fecha_inicio, fecha_fin
            
    # CORRECCIÓN 1: Este return va alineado con el for (fuera del bucle)
    return None, None

def sacarEntidades(text):
    nlp = spacy.load("es_core_news_sm")
    doc = nlp(text)
    return doc.ents

def formarQuery(entidades, fecha_inicio=None, fecha_fin=None):
    # Usamos una lista para ir guardando cada "pedazo" de la búsqueda
    query_parts = []
    
    # 1. Gestionar las fechas
    if fecha_inicio is not None and fecha_fin is not None:
        # Añadimos el objeto NumericRange a la lista
        rango = NumericRange("date", start=fecha_inicio, end=fecha_fin)
        query_parts.append(rango)
        
    elif fecha_inicio is not None and fecha_fin is None:
        # Si solo hay una fecha, lo guardamos como texto normal
        query_parts.append(f"date:{fecha_inicio}")
        
    
    # 2. Gestionar las entidades de spaCy
    for entidad in entidades:
        texto = entidad.text
        
        match entidad.label_:
            case "PER":
                query_parts.append(f"(creator:{texto} OR contributor:{texto})")
            case "LOC" | "ORG":
                query_parts.append(f"publisher:{texto}")
            case "MISC":
                query_parts.append(f"subject:{texto}")
            case _:
                pass # Ignoramos lo que no nos sirva

    query_final = " AND ".join(str(part) for part in query_parts)
    
    return query_final


if __name__ == '__main__':
    index_folder = '../whooshindex'
    query_file = None
    output_file = None
    i = 1
    fecha = False
    while (i < len(sys.argv)):
        if sys.argv[i] == '-index':
            index_folder = sys.argv[i+1]
            i = i + 1
        elif sys.argv[i] == '-info':
            fecha = True
        elif sys.argv[i] == '-output':
            output_file = sys.argv[i+1]
            i = i + 1
        elif sys.argv[i] == '-infoNeeds':
            query_file = sys.argv[i+1]
            i = i + 1
        i = i + 1

    searcher = MySearcher(index_folder)  # You can change the model type if needed

    #Caso en el que la query se introduce por teclado
    if(query_file is None):
        pregunta = input('Introduce a query: ')
        entidades = sacarEntidades(pregunta)
        fecha_inicio, fecha_fin = sacarFechas(pregunta)
        print(fecha_inicio, fecha_fin)
        query = formarQuery(entidades, fecha_inicio, fecha_fin)
        idx=1
        while pregunta != 'q':
            searcher.search(query, idx, output_file, fecha)
            pregunta = input('Introduce a query (\'q\' for exit): ')
            entidades = sacarEntidades(pregunta)
            fecha_inicio, fecha_fin = sacarFechas(pregunta)
            print(fecha_inicio, fecha_fin)
            query = formarQuery(entidades, fecha_inicio, fecha_fin)
            idx += 1
    #Caso en el que la query se introduce desde un fichero
    else:
        #Abrimos el fichero de queries y leemos todas las líneas
        with open(query_file, 'r', encoding='utf-8') as f:#encoding='utf-8' para que funcione con acentos y ñ
            queries = f.readlines()
        i = 1
        #Pasamos todas las queries al método search y vamos incrementando el índice de la query
        for query in queries:
            searcher.search(query, i, output_file, fecha)
            i += 1