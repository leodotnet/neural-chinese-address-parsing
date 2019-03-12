import vocabulary



chinese_digit = '一二三四五六七八九十百千万'

def is_digit(tok:str):

    tok = tok.strip()

    if tok.isdigit():
        return True

    if tok in chinese_digit:
        return True

    return False


def seq2chunk(seq):
    chunks = []
    label = None
    last_label = None
    start_idx = 0
    for i in range(len(seq)):
        tok = seq[i]
        label = tok[2:] if tok.startswith('B') or tok.startswith('I') else tok
        if tok.startswith('B') or last_label != label:
            if last_label == None:
                start_idx = i
            else:
                chunks.append((last_label, start_idx, i))
                start_idx = i

        last_label = label

    chunks.append((label, start_idx, len(seq)))

    return chunks

def read_chunks(filename, normal = 1):
    f = open(filename, 'r', encoding='utf-8')
    insts = []
    inst = list()
    num_inst = 0
    max_chunk_length_limit = 36
    max_chunk_length = 0
    max_char_length = 0
    for line in f:
        line = line.strip()
        if line == "":
            if inst != None:

                inst = [tuple(x) for x in inst]

                tmp = list(zip(*inst))

                x = tmp[0]
                new_x = []
                for word in x:
                    if normal == 1:
                        newword = ''
                        for c in word:
                            if is_digit(c):
                                newword += '0'
                            else:
                                newword += c
                    else:
                        newword = word

                    new_x.append(newword)


                y = [x[:2] + x[2:].lower() for x in tmp[1]]

                chunks = seq2chunk(y)

                for chunk in chunks:
                    if max_chunk_length < chunk[2] - chunk[1]:
                        max_chunk_length = chunk[2] - chunk[1]

                if max_char_length < len(x):
                    max_char_length = len(x)

                insts.append((new_x, chunks))

            inst = list()
        else:
            inst.append(line.split())
    f.close()
    print(filename + 'is loaded.','\t', 'max_chunk_length=',max_chunk_length, '\tmax_char_length:', max_char_length)
    return insts


def load_trees_from_str(tokens, normal = 1, strip_top=True):
    from trees import InternalTreebankNode, LeafTreebankNode

    tokens = tokens.replace("(", " ( ").replace(")", " ) ").split()

    def helper(index):
        trees = []

        while index < len(tokens) and tokens[index] == "(":
            paren_count = 0
            while tokens[index] == "(":
                index += 1
                paren_count += 1

            label = tokens[index]
            index += 1

            if tokens[index] == "(":
                children, index = helper(index)
                trees.append(InternalTreebankNode(label, children))
            else:
                word = tokens[index]
                if normal == 1:
                    newword = ''
                    for c in word:
                        if is_digit(c):
                            newword += '0'
                        else:
                            newword += c
                else:
                    newword = word
                index += 1
                trees.append(LeafTreebankNode(label, newword))

            while paren_count > 0:
                assert tokens[index] == ")"
                index += 1
                paren_count -= 1

        return trees, index

    trees, index = helper(0)
    assert index == len(tokens)

    if strip_top:
        for i, tree in enumerate(trees):
            if tree.label == "TOP":
                assert len(tree.children) == 1
                trees[i] = tree.children[0]

    return trees



def load_label_list(path):
    f = open(path, 'r', encoding='utf-8')
    label_list = [line.strip() for line in f]
    f.close()
    return label_list


def load_pretrain(filename : str, WORD_DIM, word_vocab : vocabulary.Vocabulary, saveemb=True):
    import numpy as np
    import parse
    import pickle

    if filename == 'none':
        print("Do not use pretrain embedding...")
        return None

    print('Loading Pretrained Embedding from ', filename,' ...')
    vocab_dic = {}
    with open(filename, encoding='utf-8') as f:
        for line in f:
            s_s = line.split()
            if s_s[0] in word_vocab.counts:
                vocab_dic[s_s[0]] = np.array([float(x) for x in s_s[1:]])
                # vocab_dic[s_s[0]] = [float(x) for x in s_s[1:]]

    unknowns = np.random.uniform(-0.01, 0.01, WORD_DIM).astype("float32")
    numbers = np.random.uniform(-0.01, 0.01, WORD_DIM).astype("float32")

    vocab_dic[parse.UNK] = unknowns
    vocab_dic[parse.NUM] = numbers



    ret_mat = np.zeros((word_vocab.size, WORD_DIM))
    unk_counter = 0
    for token_id in range(word_vocab.size):
        token = word_vocab.value(token_id)
        if token in vocab_dic:
            # ret_mat.append(vocab_dic[token])
            ret_mat[token_id] = vocab_dic[token]
        # elif parse.is_digit(token) or token == '<NUM>':
        #     ret_mat[token_id] = numbers
        else:
            # ret_mat.append(unknowns)
            ret_mat[token_id] = unknowns
            # print "Unknown token:", token
            unk_counter += 1
            #print('unk:', token)
    ret_mat = np.array(ret_mat)

    print('ret_mat shape:', ret_mat.shape)

    if saveemb:
        with open('giga.emb', "wb") as f:
            pickle.dump(ret_mat, f)

    print("{0} unk out of {1} vocab".format(unk_counter, word_vocab.size))
    print('Glove Embedding is loaded.')
    return ret_mat


def inst2chunks(inst):
    chunks = []
    x, x_chunks = inst
    for x_chunk in x_chunks:
        chunk = (x_chunk[0], x_chunk[1], x_chunk[2], x[x_chunk[1]:x_chunk[2]])
        chunks.append(chunk)

    return chunks