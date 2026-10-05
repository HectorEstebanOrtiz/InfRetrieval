"""
index.py
Author: Javier Nogueras Iso
Last update: 2024-09-07

Simple program to create an inverted index with the contents of text/xml files contained in a docs folder
This program is based on the whoosh library. See https://pypi.org/project/Whoosh/ .
Usage: python index.py -index <index folder> -docs <docs folder>
"""

#Autores: Ciro Fustero Zumeta (NIP: 900506) y Héctor Esteban Ortiz (NIP: 898030)

from datetime import datetime
from tkinter.tix import TEXT

from whoosh.index import create_in
from whoosh.fields import *


import os

import xml.etree.ElementTree as ET

from ourFilter import *


def create_folder(folder_name):
    if (not os.path.exists(folder_name)):
        os.mkdir(folder_name)

class MyIndex:
    def __init__(self,index_folder):
        language_analyzer = custom_analyzer()  # Utiliza el analizador personalizado definido en ourFilter.py
        #Hemos añadido al schema más campos para la práctica
        schema = Schema(
            path=ID(stored=True),
            identifier=ID(stored=True, unique=True), #Añadimos este campo para implrimir los id en el fichero de salida
            content=TEXT(analyzer=language_analyzer),
            creator=TEXT(analyzer=language_analyzer, stored=True), #Autor del documento
            contributor=TEXT(analyzer=language_analyzer, stored=True), #Director acargo
            publisher=TEXT(analyzer=language_analyzer, stored=True), #Departamento publicador
            date=TEXT(analyzer=language_analyzer, stored=True), #Año de publicación
            title=TEXT(analyzer=language_analyzer, stored=True), 
            subject=TEXT(analyzer=language_analyzer, stored=True),
            description=TEXT(analyzer=language_analyzer, stored=True),
            modtime=STORED,  # Campo STORED para la fecha de modificación
        )
        create_folder(index_folder)
        index = create_in(index_folder, schema)
        self.writer = index.writer()

    def index_docs(self,docs_folder):
        if (os.path.exists(docs_folder)):
            for file in sorted(os.listdir(docs_folder)):
                # print(file)
                if file.endswith('.xml'):
                    self.index_xml_doc(docs_folder, file)
                elif file.endswith('.txt'):
                    self.index_txt_doc(docs_folder, file)
        self.writer.commit()

    def index_txt_doc(self, foldername,filename):
        file_path = os.path.join(foldername, filename)
        # print(file_path)
        mtime = os.path.getmtime(file_path)
        fecha_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        with open(file_path) as fp:
            text = ' '.join(line for line in fp if line)
        # print(text)
        self.writer.add_document(path=filename, content=text, modtime=fecha_str)

    def index_xml_doc(self, foldername, filename):
        file_path = os.path.join(foldername, filename)
        # print(file_path)
        mtime = os.path.getmtime(file_path)
        fecha_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        tree = ET.parse(file_path)
        root = tree.getroot()
        #Inicializamos listas para almacenar los valores de cada etiqueta
        titles, subjects, descriptions, anyos, autores, directores, departamentos, identificadores = [], [], [], [], [], [], [], []

        #Recorremos todas las etiquetas limpiando el namespace
        for elem in root.iter():
            if elem.text:
                tag_name = elem.tag.split("}")[-1].lower()
                clean_text = " ".join(elem.text.split())

                #Recogemos los valores de cada etiqueta en la lista correspondiente
                if clean_text:
                    if tag_name == "title":
                        titles.append(clean_text)
                    elif tag_name == "subject":
                        subjects.append(clean_text)
                    elif tag_name == "description":
                        descriptions.append(clean_text)
                    elif tag_name == "date":
                        anyos.append(clean_text)
                    elif tag_name == "creator":
                        autores.append(clean_text)
                    elif tag_name == "contributor":
                        directores.append(clean_text)
                    elif tag_name == "publisher":
                        departamentos.append(clean_text)
                    elif tag_name == "identifier":
                        identificadores.append(clean_text)

        
        #Añadimos el documento al índice con los campos correspondientes
        self.writer.add_document(path=filename,title=" ".join(titles), subject=" ".join(subjects), description=" ".join(descriptions), date=" ".join(anyos), creator=" ".join(autores), contributor=" ".join(directores), publisher=" ".join(departamentos), identifier=" ".join(identificadores), modtime=fecha_str)

if __name__ == '__main__':

    index_folder = '../whooshindex'
    docs_folder = '../docs'
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-index':
            index_folder = sys.argv[i + 1]
            i = i + 1
        elif sys.argv[i] == '-docs':
            docs_folder = sys.argv[i + 1]
            i = i + 1
        i = i + 1

    my_index = MyIndex(index_folder)
    my_index.index_docs(docs_folder)