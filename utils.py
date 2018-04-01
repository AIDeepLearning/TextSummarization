import json

from config import UNK
from preprocess.iterator import end_token
import numpy as np
import pickle


def load_dict(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except:
        with open(filename, 'r') as f:
            return pickle.load(f)


def load_inverse_dict(dict_path):
    orig_dict = load_dict(dict_path)
    idict = {}
    try:
        for words, idx in orig_dict.iteritems():
            idict[idx] = words
    except:
        for words, idx in orig_dict.items():
            idict[idx] = words
    return idict


def seq2words(seq, inverse_target_dictionary):
    words = []
    for w in seq:
        if w == end_token:
            break
        if w in inverse_target_dictionary:
            words.append(inverse_target_dictionary[w])
        else:
            words.append(UNK)
    return ' '.join(words)


# batch preparation of a given sequence
def prepare_batch(seqs_x, maxlen=None):
    # seqs_x: a list of sentences
    lengths_x = [len(s) for s in seqs_x]
    
    if maxlen is not None:
        new_seqs_x = []
        new_lengths_x = []
        for l_x, s_x in zip(lengths_x, seqs_x):
            if l_x <= maxlen:
                new_seqs_x.append(s_x)
                new_lengths_x.append(l_x)
        lengths_x = new_lengths_x
        seqs_x = new_seqs_x
        
        if len(lengths_x) < 1:
            return None, None
    
    batch_size = len(seqs_x)
    
    x_lengths = np.array(lengths_x)
    maxlen_x = np.max(x_lengths)
    
    x = np.ones((batch_size, maxlen_x)).astype('int32') * end_token
    
    for idx, s_x in enumerate(seqs_x):
        x[idx, :lengths_x[idx]] = s_x
    return x, x_lengths


# batch preparation of a given sequence pair for training
def prepare_pair_batch(seqs_x, seqs_y, x_max_length=None, y_max_length=None):
    # seqs_x, seqs_y: a list of sentences
    lengths_x = [len(s) for s in seqs_x]
    lengths_y = [len(s) for s in seqs_y]
    
    if x_max_length is not None:
        new_seqs_x = []
        new_lengths_x = []
        for l_x, s_x in zip(lengths_x, seqs_x):
            if l_x <= x_max_length:
                new_seqs_x.append(s_x)
                new_lengths_x.append(l_x)
        lengths_x = new_lengths_x
        seqs_x = new_seqs_x
    
    if y_max_length is not None:
        new_seqs_y = []
        new_lengths_y = []
        for l_y, s_y in zip(lengths_y, seqs_y):
            if l_y <= y_max_length:
                new_seqs_y.append(s_y)
                new_lengths_y.append(l_y)
        lengths_y = new_lengths_y
        seqs_y = new_seqs_y
        
        if len(lengths_x) < 1 or len(lengths_y) < 1:
            return None, None, None, None
    
    batch_size = len(seqs_x)
    
    x_lengths = np.array(lengths_x)
    y_lengths = np.array(lengths_y)
    
    maxlen_x = np.max(x_lengths)
    maxlen_y = np.max(y_lengths)
    
    x = np.ones((batch_size, maxlen_x)).astype('int32') * end_token
    y = np.ones((batch_size, maxlen_y)).astype('int32') * end_token
    
    for idx, [s_x, s_y] in enumerate(zip(seqs_x, seqs_y)):
        x[idx, :lengths_x[idx]] = s_x
        y[idx, :lengths_y[idx]] = s_y
    return x, x_lengths, y, y_lengths
