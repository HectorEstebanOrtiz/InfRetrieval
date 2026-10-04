"""
search.py
Author: Javier Nogueras Iso
Last update: 2024-09-07

Program to search a free text query on a previously created inverted index.
This program is based on the whoosh library. See https://pypi.org/project/Whoosh/ .
Usage: python search.py -index <index folder>
"""

import sys

from whoosh.qparser import QueryParser
from whoosh.qparser import MultifieldParser
from whoosh.qparser import OrGroup
from whoosh import scoring
from ourFilter import *
import whoosh.index as index

class MySearcher:
    def __init__(self, index_folder, model_type = 'tfidf'):
        ix = index.open_dir(index_folder)
        if model_type == 'tfidf':
            # Apply a vector retrieval model as default
            self.searcher = ix.searcher(weighting=scoring.TF_IDF())
        else:
            # Apply the probabilistic BM25F model, the default model in searcher method
            self.searcher = ix.searcher()
        self.parser = MultifieldParser(["content", "title", "subject", "description", "date", "creator", "contributor", "publisher", "identifier"], ix.schema, group = OrGroup)

    def search(self, query_text, query_idx, output, show_info=False):
        query = self.parser.parse(query_text)
        results = self.searcher.search(query, limit = None)
        print(f'Query: {query}')
        
        i = 1
        for result in results:
            if output is not None:
                with open(output, 'a') as f:
                    print(f'{query_idx}     {result.get("identifier")}', file=f)
            else:
                print(f'{i} - File path: {result.get("path")}, Similarity score: {result.score}')
            if show_info:
                print(f'  Last Date Modified: {result.get("modtime")}')
            i += 1
            if i>100 and output is not None:
                break
        if output is not None:
            print('Check output file for results')

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

    searcher = MySearcher(index_folder)

    #query = 'System engineering'
    if(query_file is None):
        query = input('Introduce a query: ')
        idx=1
        while query != 'q':
            searcher.search(query, idx, output_file, fecha)
            query = input('Introduce a query (\'q\' for exit): ')
            idx += 1
    else:
        with open(query_file, 'r') as f:
            queries = f.readlines()
        i = 1
        for query in queries:
            searcher.search(query, i, output_file, fecha)
            i += 1