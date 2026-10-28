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

nlp = spacy.load("es_core_news_md") #Hemos decidido usar el modelo medio para que tenga menos equivocaciones (Antes ponia algunos nombres como lugares y lugares como nombres)

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
        self.parser = MultifieldParser(["content", "title", "subject", "description", "creator", "contributor", "publisher", "identifier", "date", "west", "east", "north", "south"], ix.schema, group = OrGroup)

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
                        print(f'{query_idx}     {result.get("identifier")}', file=f)
                        if show_info:
                            print(f'   Last Date Modified: {result.get("modtime")}')
                print('Check output file for results')
        else:
            for i, result in enumerate(results[:100], start=1):
                print(f'{i} - File path: {result.get("path")}, Similarity score: {result.score}')
                if show_info:
                    print(f'   Last Date Modified: {result.get("modtime")}')

#Funcion auxiliar que extrae las fechas de la pregunta. Devuelve las fechas y la pregunta sin las fechas
def sacarFechas(text):
    anio_actual = datetime.now().year #Usamos la fecha actual para preguntas tipo "en los ultimos 20 años"
    texto_limpio = text

    #Patrones para encontrar las fechas relativas
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

    #Calculamos la fecha referente
    for patron, tipo in patronesRelativos:
        match = re.search(patron, texto_limpio, re.IGNORECASE)
        if match:
            cantidad_anios = int(match.group(1))
            #Restamos o sumamos la fecha relativa a la actual para sacar la fecha referente
            if tipo == "menos":
                fecha_fin = anio_actual
                fecha_inicio = anio_actual - cantidad_anios
            elif tipo == "mas":
                fecha_fin = anio_actual - cantidad_anios
                fecha_inicio = None
            elif tipo == "exacto":
                fecha_inicio = anio_actual - cantidad_anios
                fecha_fin = anio_actual - cantidad_anios

            #Eliminamos el fragmento de fecha del texto original
            texto_limpio = (
                texto_limpio[: match.start()] + texto_limpio[match.end() :]
            ).strip()
            return fecha_inicio, fecha_fin, texto_limpio

    #Patrones para sacar el año referente o el intervalo entre años
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
            #Eliminamos las fechas del texto
            texto_limpio = (
                texto_limpio[: match.start()] + texto_limpio[match.end() :]
            ).strip()
            return fecha_inicio, fecha_fin, texto_limpio

    return None, None, texto_limpio

#Funcion auxiliar que invoca a spacy para extraer las entidades y conceptos utiles de la pregunta
def sacarEntidades(texto_limpio):
    #Procesa directamente el texto limpio
    doc = nlp(texto_limpio)

    #Extraer entidades nombradas
    entidades = list(doc.ents)

    #Extraer conceptos utiles (sustantivos y adjetivos fuera de las entidades y stopwords)
    conceptos_libres = [
        token.text
        for token in doc
        if token.pos_ in ["NOUN", "ADJ"]
        and not token.is_stop
        and not token.ent_type_
    ]

    return entidades, conceptos_libres

#Funcion auxiliar que extrae el tipo de documento que buscamos (tesis, tfg o pfc, tfm)
def sacarTipo(text):
    patrones = [
        (r'\btesis\b', "type:tesis"),
        (r'\b(?:tfg|(?:trabajos?\s+de\s+)?fin de grado)\b', "type:TFG type:PFC"), 
        (r'\b(?:tfm|(?:trabajos?\s+de\s+)?fin de m[aá]ster)\b', "type:TFM"),
        (r'\btrabajos?\b', "type:TFG type:PFC type:TFM")
    ]

    tipos_encontrados = []
    texto_limpio = text

    #Recorremos el texto buscando el tipo buscado (Utilizamos una lista para permitir que se busque mas de un tipo)
    for patron, tipo in patrones:
        if re.search(patron, texto_limpio, re.IGNORECASE):
            #Guardamos el tipo encontrado en la lista
            tipos_encontrados.append(tipo)
            
            #Borramos la palabra del texto
            texto_limpio = re.sub(patron, "", texto_limpio, flags=re.IGNORECASE)
            
    #Limpiamos los espacios sobrantes al terminar todos los patrones
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
    
    #Si hemos encontrado al menos un tipo:
    if tipos_encontrados:
        #Los unimos con un espacio
        query_tipos = "(" + " ".join(tipos_encontrados) + ")"
        return query_tipos, texto_limpio
        
    return None, texto_limpio

#Funcion auxiliar que nos devuelve el idioma que estamos buscando
def sacarIdioma(text):
    #Definimos los diferentes idiomas que vamos a detectar
    patrones = [
        (r'\bingl[eé]s\b', 'language:"eng"'),
        (r'\bespañol\b', 'language:"spa"'),
        (r'\bfranc[eé]s\b', 'language:"fre"'),
        (r'\balem[aá]n\b', 'language:"ger"'),
        (r'\bitaliano\b', 'language:"ita"')
    ]
    
    lgn_encontrados = []
    texto_limpio = text

    #Como con los tipos, permitimos más de un idioma
    for patron, lgn in patrones:
        if re.search(patron, texto_limpio, re.IGNORECASE):
            #Guardamos el tipo encontrado en la lista
            lgn_encontrados.append(lgn)
            
            #Borramos la palabra del texto
            texto_limpio = re.sub(patron, "", texto_limpio, flags=re.IGNORECASE)
            
    #Limpiamos los espacios sobrantes al terminar todos los patrones
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
    
    #Si hemos encontrado al menos un tipo:
    if lgn_encontrados:
        #Los unimos con un espacio
        query_lgn = "(" + " ".join(lgn_encontrados) + ")"
        return query_lgn, texto_limpio
        
    return None, texto_limpio

#Funcion auxiliar que forma la query que usaremos para buscar en Woosh
def formarQuery(entidades, conceptos_libres, fecha_inicio=None, fecha_fin=None, tipo_doc=None, lgn = None):
    query_parts = []
    
    #Añadimos las fechas a la query
    if fecha_inicio is not None or fecha_fin is not None:
        rango_fecha = NumericRange("date", start=fecha_inicio, end=fecha_fin)
        query_parts.append(rango_fecha)
        
    #Añadimos el tipo a la query
    if tipo_doc is not None:
        query_parts.append(f"{tipo_doc}")

    #Añadimos el idioma a la query
    if lgn is not None:
        query_parts.append(f"{lgn}")
        
    #Añadimos las entidades de spacy a la query
    for entidad in entidades:
        texto = entidad.text
        match entidad.label_:
            #Si es una persona la buscamos como creador, director o tema del documento (Esto es posible si es alguien famoso)
            case "PER":
                query_parts.append(f"creator:({texto}) contributor:({texto}) title:({texto}) description:({texto})")
            #Si es una organizacion o lugar lo buscamos como lugar de publicacion o tema del documento (Esto es posible si el documeto va sobre la org o el lugar)
            case "LOC" | "ORG":
                query_parts.append(f"publisher:({texto}) title:({texto}) description:({texto})")
            #Si no lo detecta como ninguna de las anteriores, lo buscamos como asignatura o tema
            case "MISC":
                query_parts.append(f"subject:({texto}) title:({texto}) description:({texto})")
            case _:
                pass

    #Añadimos los conceptos libres a la query
    if conceptos_libres:
        texto_libre = " ".join(conceptos_libres)
        #Los vamos a buscar como tema del documeto, asignatura o lugar de la publicacion (Esto porque cosas como informática no las detecta de por si spacy)
        sub_query = f"title:({texto_libre}) description:({texto_libre}) subject:({texto_libre}) publisher:({texto_libre})"
        query_parts.append(sub_query)

    query_final = " ".join(str(part) for part in query_parts)
    return query_final

#Funcion auxiliar que extrae los campos necesarios del fichero de entrada
def leerNecesidadesInformacion(ruta_fichero):
    consultas = []
    #Parseamos el fichero XML
    tree = ET.parse(ruta_fichero)
    root = tree.getroot()
    
    #Buscamos todos los bloques <informationNeed>
    for info_need in root.findall('informationNeed'):
        #Extraemos el texto de <identifier> y <text>
        identificador = info_need.find('identifier').text.strip()
        texto = info_need.find('text').text.strip()
        
        #Lo guardamos como una tupla (ID, Pregunta)
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

    #Caso en el que la necesidad de informacion se introduce por teclado
    if(query_file is None):
        pregunta = input('Introduce tu necesidad: ')
        fecha_inicio, fecha_fin, pregunta = sacarFechas(pregunta) #Sacamos las fechas
        tipo_trabajo, pregunta = sacarTipo(pregunta) #Sacamos el tipo
        lgn, pregunta = sacarIdioma(pregunta) #Sacamos el idioma
        entidades, conceptos_libres = sacarEntidades(pregunta) #Sacamos las entidades y los conceptos
        query = formarQuery(entidades,conceptos_libres, fecha_inicio, fecha_fin, tipo_trabajo, lgn) #Formamos la query
        idx=1
        while pregunta != 'q':
            searcher.search(query, idx, output_file, fecha)
            pregunta = input('Introduce tu necesidad (\'q\' for exit): ')
            fecha_inicio, fecha_fin, pregunta = sacarFechas(pregunta) #Sacamos las fechas
            tipo_trabajo, pregunta = sacarTipo(pregunta) #Sacamos el tipo
            lgn, pregunta = sacarIdioma(pregunta) #Sacamos el idioma
            entidades, conceptos_libres = sacarEntidades(pregunta) #Sacamos las entidades y los conceptos
            query = formarQuery(entidades,conceptos_libres, fecha_inicio, fecha_fin, tipo_trabajo, lgn) #Formamos la query
            idx += 1
    #Caso en el que las necesidades de informacion se introducen desde un fichero
    else:
        lista_consultas = leerNecesidadesInformacion(query_file)
        for idx, pregunta in lista_consultas:
            fecha_inicio, fecha_fin, pregunta = sacarFechas(pregunta) #Sacamos las fechas
            tipo_trabajo, pregunta = sacarTipo(pregunta) #Sacamos el tipo
            lgn, pregunta = sacarIdioma(pregunta) #Sacamos el idioma
            entidades, conceptos_libres = sacarEntidades(pregunta) #Sacamos las entidades y los conceptos
            query = formarQuery(entidades,conceptos_libres, fecha_inicio, fecha_fin, tipo_trabajo, lgn) #Formamos la query
            searcher.search(query, idx, output_file, fecha)