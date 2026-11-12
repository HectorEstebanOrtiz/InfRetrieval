"""
search.py
Author: Javier Nogueras Iso
Last update: 2024-09-07

Program to search a free text query on a previously created inverted index with either a vector model (tf-idf) or OkapiBM25 model
This program is based on the gensim Python library. See https://github.com/RaRe-Technologies/gensim/#documentation .
Usage: python search.py -index <index folder> -language <english|spanish>
"""

from gensim import corpora
from gensim import models
from gensim import similarities

import index
import sys
import json
import xml.etree.ElementTree as ET

def search(index_folder, query, query_identifier = None, file = None):
    dictionary = corpora.Dictionary.load(index.get_dictionary_file_name(index_folder))

    query_document = index.generate_terms(query)
    print('query words: ', query_document)
    query_bow = dictionary.doc2bow(query_document)
    print('query bow: ', query_bow)

    index_matrix = similarities.MatrixSimilarity.load(index.get_index_file_name(index_folder))
    model = models.TfidfModel.load(index.get_model_file_name(index_folder))

    print('query tfidf vector: ',model[query_bow])
    sims = index_matrix[model[query_bow]]

    print('Returned documents:')

    # Load the file_paths to display meaningful results
    with open(index.get_paths_file_name(index_folder), 'r') as f:
        file_paths = json.load(f)

    i = 1
    for document_number, score in sorted(enumerate(sims), key=lambda x: x[1], reverse=True):
        if score == 0.0 or i > 100:
            break
        url = 'http://zaguan.unizar.es/record/' + file_paths[document_number].replace('oai_zaguan.unizar.es_','').replace('.xml','')
        if(file is not None):
            with open(file, 'a') as f:
                f.write(f'{query_identifier}\t{url}\n')
        else:
            print(f'{i} - File path: {file_paths[document_number]}, Similarity score: {score}')
        i += 1


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
    index_folder = '../gensimindex'
    query_file = None
    output_file = None
    i = 1
    while (i < len(sys.argv)):
        if sys.argv[i] == '-index':
            index_folder = sys.argv[i+1]
            i = i + 1
        elif sys.argv[i] == '-language':
            # -language is expected to be either 'english' or 'spanish'
            index.LANGUAGE = sys.argv[i + 1]
            i = i + 1
        elif sys.argv[i] == '-infoNeeds':
            query_file = sys.argv[i + 1]
            i = i + 1
        elif sys.argv[i] == '-output':
            output_file = sys.argv[i+1]
            i = i + 1
        i = i + 1
    if query_file is not None:
        lista_consultas = leerNecesidadesInformacion(query_file)
        for idx, pregunta in lista_consultas:
            search(index_folder, pregunta, idx, output_file)

    #query = 'system engineering'
    query = input('Introduce a query: ')
    search(index_folder, query)