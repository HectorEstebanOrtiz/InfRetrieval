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
from datetime import datetime
import xml.etree.ElementTree as ET

nlp = spacy.load("es_core_news_md") #cambiamos a medio para ver si deja de confundir España con un apellido

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
            for i, result in enumerate(results[:100], start=1):
                print(f'{i} - File path: {result.get("path")}, Similarity score: {result.score}')
                if show_info:
                    print(f'   Last Date Modified: {result.get("modtime")}')

def sacarFechas(text):
    anio_actual = datetime.now().year
    texto_limpio = text

    patronesRelativos = [
        (r"\b(?:en\s+los\s+|los\s+)?[úu]ltimos\s+(\d+)\s+a[ñn]os\b", "menos"),
        (
            r"\b(?:que\s+tengan\s+|de\s+hace\s+|hace\s+|con\s+)?menos\s+de\s+(\d+)\s+a[ñn]os\b",
            "menos",
        ),
        (
            r"\b(?:que\s+tengan\s+|de\s+hace\s+|hace\s+|con\s+)?m[áa]s\s+de\s+(\d+)\s+a[ñn]os\b",
            "mas",
        ),
        (r"\b(?:de\s+)?hace\s+(\d+)\s+a[ñn]os\b", "exacto"),
    ]

    for patron, tipo in patronesRelativos:
        match = re.search(patron, texto_limpio, re.IGNORECASE)
        if match:
            cantidad_anios = int(match.group(1))

            if tipo == "menos":
                fecha_fin = anio_actual
                fecha_inicio = anio_actual - cantidad_anios
            elif tipo == "mas":
                fecha_fin = anio_actual - cantidad_anios
                fecha_inicio = None
            elif tipo == "exacto":
                fecha_inicio = anio_actual - cantidad_anios
                fecha_fin = anio_actual - cantidad_anios

            # Eliminamos el fragmento de fecha del texto original
            texto_limpio = (
                texto_limpio[: match.start()] + texto_limpio[match.end() :]
            ).strip()
            return fecha_inicio, fecha_fin, texto_limpio

    # 2. REGLAS ABSOLUTAS
    patronesAbsolutos = [
        r"\bentre\s+(?:el\s+año\s+)?(\d{4})\s+y\s+(?:el\s+año\s+)?(\d{4})\b",
        r"\b(?:de|desde)\s+(?:el(?:\s+año)?\s+)?(\d{4})\s+hasta\s+(?:el(?:\s+año)?\s+)?(\d{4})\b",
        r"\b(?:de|del|desde)\s+(\d{4})\s+(?:a|al)\s+(\d{4})\b",
        r'\b(?:(?:en|de|del)(?:\s+el)?(?:\s+año)?|año)\s+(\d{4})\b',
    ]

    for patron in patronesAbsolutos:
        match = re.search(patron, texto_limpio, re.IGNORECASE)
        if match:
            grupos = match.groups()

            if len(grupos) >= 2 and grupos[1] is not None:
                fecha_inicio = int(grupos[0])
                fecha_fin = int(grupos[1])
            else:
                fecha_inicio = int(grupos[0])
                fecha_fin = int(grupos[0])

            texto_limpio = (
                texto_limpio[: match.start()] + texto_limpio[match.end() :]
            ).strip()
            return fecha_inicio, fecha_fin, texto_limpio

    return None, None, texto_limpio


def sacarEntidades(texto_limpio):
    # Procesa directamente el texto sin los fragmentos de fechas
    doc = nlp(texto_limpio)

    # 1. Extraer entidades nombradas
    entidades = list(doc.ents)

    # 2. Extraer conceptos libres (sustantivos y adjetivos fuera de entidades y stopwords)
    conceptos_libres = [
        token.text
        for token in doc
        if token.pos_ in ["NOUN", "ADJ"]
        and not token.is_stop
        and not token.ent_type_
    ]

    return entidades, conceptos_libres
    
def sacarTipo(text):
    patrones = [
        (r'\btesis\b', "type:tesis"),
        # Quitamos los paréntesis de aquí porque envolveremos todo junto al final
        (r'\b(?:tfg|(?:trabajos?\s+de\s+)?fin de grado)\b', "type:TFG type:PFC"), 
        (r'\b(?:tfm|(?:trabajos?\s+de\s+)?fin de m[aá]ster)\b', "type:TFM"),
        (r'\btrabajos?\b', "type:TFG type:PFC type:TFM")
    ]
    
    tipos_encontrados = []
    texto_limpio = text
    
    for patron, tipo in patrones:
        if re.search(patron, texto_limpio, re.IGNORECASE):
            # Guardamos el tipo encontrado en la lista
            tipos_encontrados.append(tipo)
            
            # Borramos la palabra del texto
            texto_limpio = re.sub(patron, "", texto_limpio, flags=re.IGNORECASE)
            
    # Limpiamos los espacios sobrantes al terminar todos los patrones
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
    
    # Si hemos encontrado al menos un tipo (o varios)
    if tipos_encontrados:
        # Los unimos con un espacio y lo envolvemos TODO en un gran paréntesis
        query_tipos = "(" + " ".join(tipos_encontrados) + ")"
        return query_tipos, texto_limpio
        
    return None, texto_limpio

def sacarIdioma(text):
    patrones = [
        (r'\bingl[eé]s\b', 'language:"eng"'),
        (r'\bespañol\b', 'language:"spa"'),
        (r'\bfranc[eé]s\b', 'language:"fre"'),
        (r'\balem[aá]n\b', 'language:"ger"'),
        (r'\bitaliano\b', 'language:"ita"')
    ]
    
    lgn_encontrados = []
    texto_limpio = text
    
    for patron, lgn in patrones:
        if re.search(patron, texto_limpio, re.IGNORECASE):
            # Guardamos el tipo encontrado en la lista
            lgn_encontrados.append(lgn)
            
            # Borramos la palabra del texto
            texto_limpio = re.sub(patron, "", texto_limpio, flags=re.IGNORECASE)
            
    # Limpiamos los espacios sobrantes al terminar todos los patrones
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
    
    # Si hemos encontrado al menos un tipo (o varios)
    if lgn_encontrados:
        # Los unimos con un espacio y lo envolvemos TODO en un gran paréntesis
        query_lgn = "(" + " ".join(lgn_encontrados) + ")"
        return query_lgn, texto_limpio
        
    return None, texto_limpio

def formarQuery(entidades, conceptos_libres, fecha_inicio=None, fecha_fin=None, tipo_doc=None, lgn = None):
    query_parts = []
    
    # 1. Gestionar las fechas
    if fecha_inicio is not None or fecha_fin is not None:
        rango_fecha = NumericRange("date", start=fecha_inicio, end=fecha_fin)
        query_parts.append(rango_fecha)
        
    # 2. Gestionar el tipo de documento (Tesis, TFG, etc.)
    if tipo_doc is not None:
        query_parts.append(f"{tipo_doc}")
    
    if lgn is not None:
        query_parts.append(f"{lgn}")
        
    # 3. Gestionar las entidades de spaCy (Añadido el OR)
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
                pass

    # 4. Gestionar los conceptos libres (Añadidos los OR)
    if conceptos_libres:
        # Filtramos para que palabras como "tesis" o "trabajo" no se busquen doble
        conceptos_filtrados = [c for c in conceptos_libres if c.lower() not in ["tesis", "trabajo", "tfg", "tfm"]]
        
        if conceptos_filtrados:
            texto_libre = " ".join(conceptos_filtrados)
            sub_query = f"(title:({texto_libre}) OR description:({texto_libre}) OR subject:({texto_libre}) OR publisher:({texto_libre}))"
            query_parts.append(sub_query)

    query_final = " OR ".join(str(part) for part in query_parts)
    return query_final

def leerNecesidadesInformacion(ruta_fichero):
    consultas = []
    # Parseamos el fichero XML
    tree = ET.parse(ruta_fichero)
    root = tree.getroot()
    
    # Buscamos todos los bloques <informationNeed>
    for info_need in root.findall('informationNeed'):
        # Extraemos el texto de <identifier> y <text>
        identificador = info_need.find('identifier').text.strip()
        texto = info_need.find('text').text.strip()
        
        # Lo guardamos como una tupla (ID, Pregunta)
        consultas.append((identificador, texto))
        
    return consultas

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
        fecha_inicio, fecha_fin, pregunta = sacarFechas(pregunta)
        tipo_trabajo, pregunta = sacarTipo(pregunta)
        lgn, pregunta = sacarIdioma(pregunta)
        entidades, conceptos_libres = sacarEntidades(pregunta)
        print(fecha_inicio, fecha_fin)
        query = formarQuery(entidades,conceptos_libres, fecha_inicio, fecha_fin, tipo_trabajo, lgn)
        idx=1
        while pregunta != 'q':
            searcher.search(query, idx, output_file, fecha)
            pregunta = input('Introduce a query (\'q\' for exit): ')
            fecha_inicio, fecha_fin, pregunta = sacarFechas(pregunta)
            tipo_trabajo, pregunta = sacarTipo(pregunta)
            lgn, pregunta = sacarIdioma(pregunta)
            entidades, conceptos_libres = sacarEntidades(pregunta)
            print(fecha_inicio, fecha_fin)
            query = formarQuery(entidades,conceptos_libres, fecha_inicio, fecha_fin, tipo_trabajo, lgn)
            idx += 1
    #Caso en el que la query se introduce desde un fichero
    else:
        #Abrimos el fichero de queries y leemos todas las líneas
        #with open(query_file, 'r', encoding='utf-8') as f:#encoding='utf-8' para que funcione con acentos y ñ
        #    queries = f.readlines()
        #i = 1
        #Pasamos todas las queries al método search y vamos incrementando el índice de la query
        #for query in queries:
        #    searcher.search(query, i, output_file, fecha)
        #    i += 1
        #MODIFICO ESTO PARA PROBAR EL FICHERO DE ENTRADA Y ASI PERMITIR TAMBIEN LAS PRUEBAS UNITARIAS
        lista_consultas = leerNecesidadesInformacion(query_file)
        for idx, pregunta in lista_consultas:
            fecha_inicio, fecha_fin, pregunta = sacarFechas(pregunta)
            tipo_trabajo, pregunta = sacarTipo(pregunta)
            lgn, pregunta = sacarIdioma(pregunta)
            entidades, conceptos_libres = sacarEntidades(pregunta)
            query = formarQuery(entidades,conceptos_libres, fecha_inicio, fecha_fin, tipo_trabajo, lgn)
            searcher.search(query, idx, output_file, fecha)