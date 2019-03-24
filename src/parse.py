import functools

import dynet as dy
import numpy as np

import trees
import util


START = "<START>"
STOP = "<STOP>"
UNK = "</s>"
NUM = "<NUM>"
XX = "XX"
EMPTY = "<ept>"


def augment(scores, oracle_index):
    assert isinstance(scores, dy.Expression)
    shape = scores.dim()[0]
    assert len(shape) == 1
    increment = np.ones(shape)
    increment[oracle_index] = 0
    return scores + dy.inputVector(increment)



class Feedforward(object):
    def __init__(self, model, input_dim, hidden_dims, output_dim):
        self.spec = locals()
        self.spec.pop("self")
        self.spec.pop("model")

        self.model = model.add_subcollection("Feedforward")

        self.weights = []
        self.biases = []
        dims = [input_dim] + hidden_dims + [output_dim]
        for prev_dim, next_dim in zip(dims, dims[1:]):
            self.weights.append(self.model.add_parameters((next_dim, prev_dim)))
            self.biases.append(self.model.add_parameters(next_dim))

    def param_collection(self):
        return self.model

    @classmethod
    def from_spec(cls, spec, model):
        return cls(model, **spec)

    def __call__(self, x):
        for i, (weight, bias) in enumerate(zip(self.weights, self.biases)):
            weight = dy.parameter(weight)
            bias = dy.parameter(bias)
            x = dy.affine_transform([bias, weight, x])
            if i < len(self.weights) - 1:
                x = dy.rectify(x)
        return x


class ChartDynamicRBTConstraintParser(object):
    def __init__(
            self,
            model,
            tag_vocab,
            word_vocab,
            label_vocab,
            tag_embedding_dim,
            word_embedding_dim,
            lstm_layers,
            lstm_dim,
            label_hidden_dim,
            dropout,
            pretrainemb,
            chunk_encoding = 1,
            train_constraint = True,
            decode_constraint = True,
            zerocostchunk = 0,
            nontlabelstyle = 0,
    ):
        self.spec = locals()
        self.spec.pop("self")
        self.spec.pop("model")

        self.model = model.add_subcollection("Parser")
        self.tag_vocab = tag_vocab
        self.word_vocab = word_vocab
        self.label_vocab = label_vocab
        self.lstm_dim = lstm_dim

        self.tag_embeddings = self.model.add_lookup_parameters(
            (tag_vocab.size, tag_embedding_dim))
        self.word_embeddings = self.model.add_lookup_parameters(
            (word_vocab.size, word_embedding_dim))

        if pretrainemb[0] != 'none':
            print('Init Lookup table with pretrain emb')
            self.word_embeddings.init_from_array(pretrainemb[1])

        self.lstm = dy.BiRNNBuilder(
            lstm_layers,
            tag_embedding_dim + word_embedding_dim,
            2 * lstm_dim,
            self.model,
            dy.VanillaLSTMBuilder)

        self.CompFwdRNN = dy.LSTMBuilder(lstm_layers, 2 * lstm_dim, 2 * lstm_dim, model)
        self.CompBwdRNN = dy.LSTMBuilder(lstm_layers, 2 * lstm_dim, 2 * lstm_dim, model)

        self.pW_comp = model.add_parameters((lstm_dim * 2, lstm_dim * 4))
        self.pb_comp = model.add_parameters((lstm_dim * 2,))


        self.f_label = Feedforward(
            self.model, 2 * lstm_dim, [label_hidden_dim], label_vocab.size - 1)

        self.dropout = dropout

        self.chunk_encoding = chunk_encoding

        self.train_constraint = train_constraint
        self.decode_constraint = decode_constraint
        self.zerocostchunk = zerocostchunk
        self.nontlabelstyle = nontlabelstyle

    def param_collection(self):
        return self.model

    @classmethod
    def from_spec(cls, spec, model):
        return cls(model, **spec)




    def parse(self, sentence, gold=None, gold_chunks=None, latentscope=None):
        is_train = gold is not None

        if is_train:
            self.lstm.set_dropout(self.dropout)
        else:
            self.lstm.disable_dropout()

        embeddings = []
        for tag, word in [(START, START)] + sentence + [(STOP, STOP)]:
            tag_embedding = self.tag_embeddings[self.tag_vocab.index(tag)]
            if word not in (START, STOP):
                count = self.word_vocab.count(word)
                if not count or (is_train and np.random.rand() < 1 / (1 + count)):
                    word = UNK
            word_embedding = self.word_embeddings[self.word_vocab.index(word)]
            embeddings.append(dy.concatenate([tag_embedding, word_embedding]))

        lstm_outputs = self.lstm.transduce(embeddings)

        W_comp = dy.parameter(self.pW_comp)
        b_comp = dy.parameter(self.pb_comp)

        @functools.lru_cache(maxsize=None)
        def get_span_encoding(left, right):
            if self.chunk_encoding == 2:
                return get_span_encoding_chunk(left, right)
            forward = (
                lstm_outputs[right][:self.lstm_dim] -
                lstm_outputs[left][:self.lstm_dim])
            backward = (
                lstm_outputs[left + 1][self.lstm_dim:] -
                lstm_outputs[right + 1][self.lstm_dim:])


            bi = dy.concatenate([forward, backward])

            return bi

        @functools.lru_cache(maxsize=None)
        def get_span_encoding_chunk(left, right):

            fw_init = self.CompFwdRNN.initial_state()
            bw_init = self.CompBwdRNN.initial_state()

            fwd_exp = fw_init.transduce(lstm_outputs[left:right])
            bwd_exp = bw_init.transduce(reversed(lstm_outputs[left:right]))

            bi = dy.concatenate([fwd_exp[-1], bwd_exp[-1]])
            chunk_rep = dy.rectify(dy.affine_transform([b_comp, W_comp, bi]))

            return chunk_rep

        @functools.lru_cache(maxsize=None)
        def get_label_scores(left, right):
            non_empty_label_scores = self.f_label(get_span_encoding(left, right))
            return dy.concatenate([dy.zeros(1), non_empty_label_scores])



        def helper(force_gold):
            if force_gold:
                assert is_train

            chart = {}
            label_scores_span_max = {}

            for length in range(1, len(sentence) + 1):
                for left in range(0, len(sentence) + 1 - length):
                    right = left + length

                    label_scores = get_label_scores(left, right)

                    if is_train:
                        oracle_label = gold.oracle_label(left, right)
                        oracle_label_index = self.label_vocab.index(oracle_label)



                    if force_gold:
                        label = oracle_label
                        label_index = oracle_label_index
                        label_score = label_scores[label_index]

                        if self.nontlabelstyle == 3:
                            label_scores_np = label_scores.npvalue()
                            argmax_label_index = int(
                                label_scores_np.argmax() if length < len(sentence) else
                                label_scores_np[1:].argmax() + 1)
                            argmax_label = self.label_vocab.value(argmax_label_index)
                            label = argmax_label
                            label_score = label_scores[argmax_label_index]

                    else:
                        if is_train:
                            label_scores = augment(label_scores, oracle_label_index)
                        label_scores_np = label_scores.npvalue()
                        #argmax_score = dy.argmax(label_scores, gradient_mode="straight_through_gradient")
                        #dy.dot_product()
                        argmax_label_index = int(
                            label_scores_np.argmax() if length < len(sentence) else
                            label_scores_np[1:].argmax() + 1)
                        argmax_label = self.label_vocab.value(argmax_label_index)
                        label = argmax_label
                        label_score = label_scores[argmax_label_index]

                    if length == 1:
                        tag, word = sentence[left]
                        tree = trees.LeafParseNode(left, tag, word)
                        if label:
                            tree = trees.InternalParseNode(label, [tree])
                        chart[left, right] = [tree], label_score
                        label_scores_span_max[left, right] = [tree], label_score
                        continue

                    if force_gold:
                        oracle_splits = gold.oracle_splits(left, right)

                        if (len(label) > 0 and (label[0].endswith("'") or label[0] == EMPTY)) and latentscope[0] <= left <= right <= latentscope[1]: #  if label == (EMPTY,) and latentscope[0] <= left <= right <= latentscope[1]: # and label != ():
                            # Latent during Training
                            #if self.train_constraint:

                            # if self.train_constraint:
                            #     oracle_splits = [(oracle_splits[0], 0), (oracle_splits[-1], 1)]
                            # else:
                            #     #oracle_splits = [(p, 0) for p in oracle_splits] + [(p, 1) for p in oracle_splits]  # it is not correct
                            #     pass

                            oracle_splits = [(oracle_splits[0], 0), (oracle_splits[-1], 1)]
                            best_split = max(oracle_splits,
                                             key=lambda sb : #(split, branching)  #branching == 0: right branching;  1: left branching
                                             label_scores_span_max[left, sb[0]][1].value() + chart[sb[0], right][1].value() if sb[1] == 0 else
                                             chart[left, sb[0]][1].value() + label_scores_span_max[sb[0], right][1].value()
                                             )
                        else:

                            best_split = (min(oracle_splits), 0)  #by default right braching


                    else:
                        pred_range = range(left + 1, right)
                        pred_splits = [(p, 0) for p in pred_range] + [(p, 1) for p in pred_range]
                        best_split = max(pred_splits,
                                         key=lambda sb:  # (split, branching)  #branching == 0: right branching;  1: left branching
                                         label_scores_span_max[left, sb[0]][1].value() + chart[sb[0], right][1].value() if sb[1] == 0 else
                                         chart[left, sb[0]][1].value() + label_scores_span_max[sb[0], right][1].value()
                                         )

                    children_leaf = [trees.LeafParseNode(pos, sentence[pos][0], sentence[pos][1]) for pos in range(left, right)]
                    label_scores_span_max[left, right] = children_leaf, label_score



                    if best_split[1] == 0:#Right Branching
                        left_trees, left_score = label_scores_span_max[left, best_split[0]]
                        right_trees, right_score = chart[best_split[0], right]
                    else:#Left Branching
                        left_trees, left_score = chart[left, best_split[0]]
                        right_trees, right_score = label_scores_span_max[best_split[0], right]


                    children = left_trees + right_trees

                    if label:
                        children = [trees.InternalParseNode(label, children)]
                        if not label[0].endswith("'"):
                            children_leaf = [trees.InternalParseNode(label, children_leaf)]
                            label_scores_span_max[left, right] = children_leaf, label_score

                    chart[left, right] = (children, label_score + left_score + right_score)



            children, score = chart[0, len(sentence)]
            assert len(children) == 1
            return children[0], score

        tree, score = helper(False)
        if is_train:
            oracle_tree, oracle_score = helper(True)
            #assert oracle_tree.convert().linearize() == gold.convert().linearize()
            #correct = tree.convert().linearize() == gold.convert().linearize()

            if self.zerocostchunk:
                pred_chunks = tree.convert().to_chunks()
                correct =  (gold_chunks == pred_chunks)
            else:
                correct = False #(gold_chunks == pred_chunks)
            loss = dy.zeros(1) if correct else score - oracle_score
            #loss = score - oracle_score
            return tree, loss
        else:
            return tree, score



class ChartDynamicRBTChunkParser(object):
    def __init__(
            self,
            model,
            tag_vocab,
            word_vocab,
            label_vocab,
            tag_embedding_dim,
            word_embedding_dim,
            lstm_layers,
            lstm_dim,
            label_hidden_dim,
            dropout,
            pretrainemb,
            chunk_encoding = 1,
            max_chunk_length = 36,
            zero_cost_chunk = False,
    ):
        self.spec = locals()
        self.spec.pop("self")
        self.spec.pop("model")

        self.model = model.add_subcollection("Parser")
        self.tag_vocab = tag_vocab
        self.word_vocab = word_vocab
        self.label_vocab = label_vocab
        self.lstm_dim = lstm_dim

        self.tag_embeddings = self.model.add_lookup_parameters(
            (tag_vocab.size, tag_embedding_dim))
        self.word_embeddings = self.model.add_lookup_parameters(
            (word_vocab.size, word_embedding_dim))

        if pretrainemb[0] != 'none':
            print('Init Lookup table with pretrain emb')
            self.word_embeddings.init_from_array(pretrainemb[1])

        self.lstm = dy.BiRNNBuilder(
            lstm_layers,
            tag_embedding_dim + word_embedding_dim,
            2 * lstm_dim,
            self.model,
            dy.VanillaLSTMBuilder)

        self.CompFwdRNN = dy.LSTMBuilder(lstm_layers, 2 * lstm_dim, 2 * lstm_dim, model)
        self.CompBwdRNN = dy.LSTMBuilder(lstm_layers, 2 * lstm_dim, 2 * lstm_dim, model)

        self.pW_comp = model.add_parameters((lstm_dim * 2, lstm_dim * 4))
        self.pb_comp = model.add_parameters((lstm_dim * 2,))


        self.f_label = Feedforward(
            self.model, 2 * lstm_dim, [label_hidden_dim], label_vocab.size - 1)

        self.dropout = dropout

        self.chunk_encoding = chunk_encoding

        self.max_chunk_length = max_chunk_length

        self.zero_cost_chunk = zero_cost_chunk

    def param_collection(self):
        return self.model

    @classmethod
    def from_spec(cls, spec, model):
        return cls(model, **spec)




    def parse(self, sentence, gold=None, gold_chunks=None, latentscope=None):
        is_train = gold is not None

        if is_train:
            self.lstm.set_dropout(self.dropout)
        else:
            self.lstm.disable_dropout()

        embeddings = []
        for tag, word in [(START, START)] + sentence + [(STOP, STOP)]:
            tag_embedding = self.tag_embeddings[self.tag_vocab.index(tag)]
            if word not in (START, STOP):
                count = self.word_vocab.count(word)
                if not count or (is_train and np.random.rand() < 1 / (1 + count)):
                    word = UNK
            word_embedding = self.word_embeddings[self.word_vocab.index(word)]
            embeddings.append(dy.concatenate([tag_embedding, word_embedding]))

        lstm_outputs = self.lstm.transduce(embeddings)

        W_comp = dy.parameter(self.pW_comp)
        b_comp = dy.parameter(self.pb_comp)

        @functools.lru_cache(maxsize=None)
        def get_span_encoding(left, right):
            if self.chunk_encoding == 2:
                return get_span_encoding_chunk(left, right)
            forward = (
                lstm_outputs[right][:self.lstm_dim] -
                lstm_outputs[left][:self.lstm_dim])
            backward = (
                lstm_outputs[left + 1][self.lstm_dim:] -
                lstm_outputs[right + 1][self.lstm_dim:])
            return dy.concatenate([forward, backward])

        @functools.lru_cache(maxsize=None)
        def get_span_encoding_chunk(left, right):

            fw_init = self.CompFwdRNN.initial_state()
            bw_init = self.CompBwdRNN.initial_state()

            fwd_exp = fw_init.transduce(lstm_outputs[left:right])
            bwd_exp = bw_init.transduce(reversed(lstm_outputs[left:right]))

            bi = dy.concatenate([fwd_exp[-1], bwd_exp[-1]])
            chunk_rep = dy.rectify(dy.affine_transform([b_comp, W_comp, bi]))

            return chunk_rep

        @functools.lru_cache(maxsize=None)
        def get_label_scores(left, right):
            non_empty_label_scores = self.f_label(get_span_encoding(left, right))
            return dy.concatenate([dy.zeros(1), non_empty_label_scores])



        def helper(force_gold):
            '''
            labels do not contain () !!!
            :param force_gold:
            :return:
            '''


            if force_gold:
                assert is_train

            words = [trees.LeafParseNode(i, XX, sentence[i][1]) for i in range(len(sentence))]
            chart = {}


            if force_gold:

                for l, left, right in gold_chunks:
                    label = (l,)
                    label_scores = get_label_scores(left, right)

                    label_index = self.label_vocab.index(label)

                    label_score = label_scores[label_index]
                    chart[left, right] = ([trees.InternalParseChunkNode(label, words[left:right])], label_score)
            else:

                #Base case
                for length in range(1, self.max_chunk_length + 1):
                    for left in range(0, len(sentence) + 1 - length):
                        right = left + length

                        label_scores = get_label_scores(left, right)
                        label_scores_np = label_scores.npvalue()
                        argmax_label_index = int(label_scores_np[1:22].argmax() + 1)
                        argmax_label = self.label_vocab.value(argmax_label_index)
                        label = argmax_label
                        label_score = label_scores[argmax_label_index]

                        chart[left, right] = ([trees.InternalParseChunkNode(label, words[left:right])], label_score)





            for length in range(1, len(sentence) + 1):
                for left in range(0, len(sentence) + 1 - length):
                    right = left + length

                    if force_gold:
                        if (left, right) in chart:
                            tree, label_score = chart[left, right]
                            continue


                    label_scores = get_label_scores(left, right)

                    if is_train:
                        oracle_label = gold.oracle_label(left, right)
                        oracle_label_index = self.label_vocab.index(oracle_label)


                    if force_gold:
                        label = oracle_label
                        label_index = oracle_label_index
                        label_score = label_scores[label_index]
                    else:
                        if is_train:
                            label_scores = augment(label_scores, oracle_label_index)
                        label_scores_np = label_scores.npvalue()
                        argmax_label_index = int(
                            label_scores_np.argmax() if length < len(sentence) else
                            label_scores_np[1:].argmax() + 1)
                        argmax_label = self.label_vocab.value(argmax_label_index)
                        label = argmax_label
                        label_score = label_scores[argmax_label_index]


                    if force_gold:

                        oracle_splits = gold.oracle_splits2(left, right)

                        if len(oracle_splits) == 0:
                            continue
                        else:
                            if latentscope[0] <= left <= right <= latentscope[1]:
                                best_split = max(oracle_splits,
                                                 key=lambda split: chart[left, split][1].value() + chart[split, right][1].value()
                                                 if (left, split) in chart and (split, right) in chart
                                                 else float('-inf'))
                            else:
                                best_split = min(oracle_splits)


                        if (left, best_split) not in chart or (best_split, right) not in chart:
                            continue

                    else:
                        splits = [split for split in range(left + 1, right) if (left, split) in chart and (split, right) in chart]
                        if len(splits) == 0:
                            continue
                        best_split =max(splits,key=lambda split:chart[left, split][1].value() + chart[split, right][1].value())


                    left_trees, left_score = chart[left, best_split]
                    right_trees, right_score = chart[best_split, right]



                    children = left_trees + right_trees
                    curr_score = label_score + left_score + right_score
                    if label:
                        children = [trees.InternalParseNode(label, children)]

                    if (left, right) in chart:
                        existing_tree, existing_label_score = chart[left, right]
                        if existing_label_score.value() < curr_score.value():
                            chart[left, right] = (children, curr_score)
                    else:
                        chart[left, right] = (children, curr_score)

            children, score = chart[0, len(sentence)]

            assert len(children) == 1

            return children[0], score

        tree, score = helper(False)
        if is_train:
            oracle_tree, oracle_score = helper(True)

            if self.zero_cost_chunk:
                pred_chunks = tree.convert().to_chunks()
                correct = (gold_chunks == pred_chunks)
            else:
                correct = False
            loss = dy.zeros(1) if correct else score - oracle_score
            return tree, loss
        else:
            return tree, score

