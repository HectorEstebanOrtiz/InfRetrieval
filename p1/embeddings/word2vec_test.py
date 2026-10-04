"""
index.py
Author: Javier Nogueras Iso
Last update: 2023-10-14

Program to test how to represent documents and queries in terms of word vectors, and obtain a ranking of
documents more similar to the query according to this representation
This program is based on the gensim Python library and the Word2Vec tutorial:
https://radimrehurek.com/gensim/auto_examples/tutorials/run_word2vec.html
"""

import gensim.downloader as api
import os
from gensim.models import KeyedVectors
from gensim import utils
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import pprint


def load_word_vec_model():
    '''
    More information about storing and loading word vectors at https://radimrehurek.com/gensim/models/keyedvectors.html
    '''
    keyedvectors_file_name = 'vectors.kv'
    if (os.path.exists(keyedvectors_file_name)):
        # load from file
        wv = KeyedVectors.load(keyedvectors_file_name)
    else:
        # download and save for next executions
        # The source of these word vectors can be found here: https://code.google.com/archive/p/word2vec/
        wv = api.load('word2vec-google-news-300')
        wv.save(keyedvectors_file_name)

    # Examples about how to read the content of the word_vectors loaded by gensim
    print('Some examples of words encoded with word2vec:')
    for index, word in enumerate(wv.index_to_key):
        if index == 5:
            break
        print(f"word #{index}/{len(wv.index_to_key)} is {word}")
        if index == 4:
            pprint.pprint(wv[word])
    return wv


def process_text_file(foldername, filename):
    file_path = os.path.join(foldername, filename)
    # print(file_path)
    with open(file_path) as fp:
        text_array = []
        for line in fp:
            if line:
                processed_text = utils.simple_preprocess(line)
                text_array.extend(processed_text)
        # print(text_array)
        return text_array


def generate_vector_from_words(wv, words):
    '''
    :param wv: the word2vec representation of each word
    :param words: the words contained in the document/query
    :return: the final vector representing the document/query as the centroid of the normalized vectors of each word
    '''
    result = np.zeros(300)
    i = 0.0
    for word in words:
        try:
            word_vec = wv[word]
            result += l2normalize(np.asarray(word_vec))
            i += 1.0
        except KeyError:
            print(word, " does not appear in this model")
    result = result / i # Computation of the centroid
    return result


def l2normalize(doc_vector):
    # Perform L2 normalization
    l2_norm = np.linalg.norm(doc_vector, 2)
    return doc_vector / l2_norm


class Searcher:

    def generate_doc_vectors(self):
        doc_vectors = []
        if (os.path.exists(self.folder_name)):
            for file in sorted(os.listdir(self.folder_name)):
                text_array = process_text_file(self.folder_name, file)
                doc_vector = generate_vector_from_words(self.wv, text_array)
                doc_vectors.append(doc_vector)
        return doc_vectors

    def generate_query_vector(self, query):
        query_words = utils.simple_preprocess(query)
        query_vector = []
        query_vector.append(generate_vector_from_words(self.wv, query_words))
        return query_vector

    def __init__(self, folder_name):
        self.folder_name = folder_name
        self.wv = load_word_vec_model()
        self.doc_vectors = self.generate_doc_vectors()

    def search(self, query):
        query = query.strip()
        if len(query) > 0:
            query_vector = self.generate_query_vector(query)
            similarities = cosine_similarity(query_vector, self.doc_vectors)
            print('Ranking of documents according to similarity: ')
            for document_number, score in sorted(enumerate(similarities[0]), key=lambda x: x[1], reverse=True):
                print(document_number, score)


if __name__ == '__main__':

    searcher = Searcher('docs')
    query = 'workstation'
    print(f'\'{query}\' as an example of a query containing a word not contained in the collection.')
    while query != 'q':
        searcher.search(query)
        query = input('Introduce a query (\'q\' for exit): ')
