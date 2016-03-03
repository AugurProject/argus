#!/usr/bin/python3
"""
Prerequisites:
    * Get glove.6B.50d.txt from http://nlp.stanford.edu/projects/glove/
"""
# TODO: glove 300d, delete this file
from __future__ import print_function
from __future__ import division

import importlib
import sys
import csv

from keras.layers.core import Activation
from keras.models import Graph

import pysts.embedding as emb
import pysts.loader as loader
import pysts.nlp as nlp
from pysts.hyperparam import hash_params
from pysts.vocab import Vocabulary

from pysts.kerasts import graph_input_anssel
import pysts.kerasts.blocks as B
from argus.keyword_extract import tokenize


s0pad = 60
s1pad = 60


def load_set(fname, vocab=None):
    s0, s1, y, t = loader.load_anssel(fname, skip_oneclass=False)
    # s0=questions, s1=answers

    if vocab is None:
        vocab = Vocabulary(s0 + s1)

    si0 = vocab.vectorize(s0, spad=s0pad)
    si1 = vocab.vectorize(s1, spad=s1pad)
    f0, f1 = nlp.sentence_flags(s0, s1, s0pad, s1pad)
    gr = graph_input_anssel(si0, si1, y, f0, f1)

    return s0, s1, y, vocab, gr


def load_sent(q, a, vocab=None):
    s0, s1, y = [tokenize(q)], [tokenize(a)], 1
    # s0=questions, s1=answers

    if vocab is None:
        vocab = Vocabulary(s0 + s1)

    si0 = vocab.vectorize(s0, spad=s0pad)
    si1 = vocab.vectorize(s1, spad=s1pad)
    f0, f1 = nlp.sentence_flags(s0, s1, s0pad, s1pad)
    gr = graph_input_anssel(si0, si1, y, f0, f1)

    return gr


def config(module_config, params):
    c = dict()
    c['embdim'] = 50
    c['inp_e_dropout'] = 1/2
    c['e_add_flags'] = True

    c['ptscorer'] = B.mlp_ptscorer
    c['mlpsum'] = 'sum'
    c['Ddim'] = 1

    c['loss'] = 'binary_crossentropy'
    c['nb_epoch'] = 2
    module_config(c)

    for p in params:
        k, v = p.split('=')
        c[k] = eval(v)

    ps, h = hash_params(c)
    return c, ps, h


def prep_model(glove, vocab, module_prep_model, c, oact, s0pad, s1pad):
    # Input embedding and encoding
    model = Graph()
    N = B.embedding(model, glove, vocab, s0pad, s1pad, c['inp_e_dropout'], add_flags=c['e_add_flags'])

    # Sentence-aggregate embeddings
    final_outputs = module_prep_model(model, N, s0pad, s1pad, c)

    # Measurement

    if c['ptscorer'] == '1':
        # special scoring mode just based on the answer
        # (assuming that the question match is carried over to the answer
        # via attention or another mechanism)
        ptscorer = B.cat_ptscorer
        final_outputs = final_outputs[1]
    else:
        ptscorer = c['ptscorer']

    kwargs = dict()
    if ptscorer == B.mlp_ptscorer:
        kwargs['sum_mode'] = c['mlpsum']
    model.add_node(name='scoreS', input=ptscorer(model, final_outputs, c['Ddim'], N, c['l2reg'], **kwargs),
                   layer=Activation(oact))
    model.add_output(name='score', input='scoreS')
    return model


def build_model(glove, vocab, module_prep_model, c, s0pad=s0pad, s1pad=s1pad):
    if c['loss'] == 'binary_crossentropy':
        oact = 'sigmoid'
    else:
        # ranking losses require wide output domain
        oact = 'linear'

    model = prep_model(glove, vocab, module_prep_model, c, oact, s0pad, s1pad)
    model.compile(loss={'score': c['loss']}, optimizer='adam')
    return model


def eval_questions(sq, sa, labels, results, text):
    question = ''
    label = 1
    avg = 0
    avg_all = 0
    q_num = 0
    correct = 0
    n = 0
    f = open('printout_'+text+'.csv', 'wb')
    w = csv.writer(f, delimiter=',')
    for q, y, t, a in zip(sq, labels, results, sa):
        if q == question:
            n += 1
            avg = n/(n+1)*avg+t/(n+1)
            row = [q, y, t, '', a]
            w.writerow(row)
        else:
            row = [q, y, t, avg, a]
            w.writerow(row)
            if q_num != 0 and abs(label-avg) < 0.5:
                correct += 1
            question = q
            label = y
            avg = t
            q_num += 1
            n = 0
    if q_num != 0 and abs(label-avg) < 0.5:
        correct += 1

    print('precision on separate questions ('+text+'):', correct/q_num)

import pickle
if __name__ == "__main__":
    # modelname, trainf, valf = sys.argv[1:4]
    modelname, trainf, valf = 'rnn', 'data/hypev/argus/argus_train.csv', 'data/hypev/argus/argus_test.csv'
    params = sys.argv[4:]

    module = importlib.import_module('.'+modelname, 'models')
    conf, ps, h = config(module.config, params)

    print('GloVe')
    glove = emb.GloVe(N=conf['embdim'])

    print('Dataset')

    q = 'Will Donald Trump run for president of the united states ?'
    a = 'Neil Young , a Canadian citizen , is a supporter of Bernie Sanders for president of the United States of America , manager Elliot Roberts said .'
    vocab = pickle.load(open('sources/vocab.txt'))
    gr = load_sent(q, a, vocab)

    print('Model')
    model = build_model(glove, vocab, module.prep_model, conf)
    model.load_weights('sources/models/keras_model.h5')
    print('Predict')
    prediction = model.predict(gr)['score'][:, 0][0]
    print('PREDICTION', prediction)



