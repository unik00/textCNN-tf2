import torch
from torch import nn

import numpy as np
import pickle

from configs.configuration import config
from src import data_helper


class Emb(nn.Module):
    def __init__(self):
        super(Emb, self).__init__()

    @staticmethod
    def dict_to_emb(in_dict):
        key2index = dict()
        index = 0
        emb = []
        for key in in_dict:
            key2index[key] = index
            emb.append(in_dict[key])
            index += 1

        emb = torch.FloatTensor(emb)
        emb = nn.Embedding.from_pretrained(embeddings=emb, freeze=False)
        return emb, key2index

    @staticmethod
    def conf_to_emb(in_dict, freeze):
        emb = []
        for key in in_dict:
            if type(key) == int:  # need this to filter two-way dict
                assert len(in_dict) % 2 == 0
                onehot = np.zeros(len(in_dict) // 2, dtype=float)
                onehot[key] = 1.
                emb.append(onehot)
        emb = torch.FloatTensor(emb)
        emb = nn.Embedding.from_pretrained(embeddings=emb, freeze=False)

        return emb


class WordEmb(Emb):
    @staticmethod
    def load_word2vec():
        """
        Returns:
            model : a dict for mapping word embedding.
        """
        def load_obj(name):
            with open('obj/' + name + '.pkl', 'rb') as f:
                return pickle.load(f)

        print("Loading word2vec model...")

        # use the slim version in debugging mode for quick loading
        # model = KeyedVectors.load_word2vec_format('data/GoogleNews-vectors-negative300-SLIM.bin', binary=True)
        model = load_obj("word2vec_crossed")
        print("Finished loading")

        return model

    def __init__(self):
        super(WordEmb, self).__init__()

        # initialize word2vec embedding
        word2vec_dict = self.load_word2vec()
        self.word2vec_emb, self.word2vec_index = self.dict_to_emb(word2vec_dict)

    def in_dict(self, w):
        return str(w).lower() in self.word2vec_index

    def forward(self, w):
        w = str(w).lower()

        # convert word to index
        word_2_index = self.word2vec_index[str(w).lower()]
        word_2_index = torch.LongTensor([word_2_index])

        # from index, convert to embedding using word2vec_emb
        word_emb = self.word2vec_emb(word_2_index.to(config.device))

        return word_emb


class POSEmb(Emb):
    def __init__(self):
        super(POSEmb, self).__init__()

        # initialize part-of-speech dict
        self.POS_dict = data_helper.load_label_map('configs/pos_map.txt')
        self.POS_emb = self.conf_to_emb(self.POS_dict, freeze=False)

    def forward(self, pos):
        pos_emb = self.POS_emb(torch.LongTensor([self.POS_dict[pos]]).to(config.device))
        return pos_emb


class DependencyEmb(Emb):
    def __init__(self):
        super(DependencyEmb, self).__init__()
        # initialize relation dependency dict
        self.dep_dict = data_helper.load_label_map('configs/dep_map.txt')
        self.dep_emb = self.conf_to_emb(self.dep_dict, freeze=False)

    def forward(self, dep):
        assert dep != "ROOT"

        dep_emb = self.dep_emb(torch.LongTensor([self.dep_dict[dep]]).to(config.device))
        return dep_emb


class EdgeDirectionEmb(Emb):
    def __init__(self):
        super(EdgeDirectionEmb, self).__init__()
        self.edge_dir_emb = nn.Embedding(2, 2, max_norm=2)

    def forward(self, dep_dir):
        emb = self.edge_dir_emb(torch.LongTensor([dep_dir]).to(config.device)).view(1, 2)
        return emb


class PositionEmb(nn.Module):
    def __init__(self):
        super(PositionEmb, self).__init__()
        # initialize e1_offset_dict
        self.offset_index = lambda x: x + config.MAX_ABS_OFFSET
        self.offset_emb = nn.Embedding(config.MAX_ABS_OFFSET * 2, config.POSITION_DIM, max_norm=2)

    def forward(self, offset):
        emb = self.offset_emb(torch.LongTensor([self.offset_index(offset)]).to(config.device))
        return emb
