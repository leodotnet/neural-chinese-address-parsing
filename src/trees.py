import collections.abc
import parse
import util

class TreebankNode(object):
    pass

class InternalTreebankNode(TreebankNode):
    def __init__(self, label, children):
        assert isinstance(label, str)
        self.label = label

        assert isinstance(children, collections.abc.Sequence)
        assert all(isinstance(child, TreebankNode) for child in children)
        #assert children
        self.children = tuple(children)

    def to_chunks(self):
        raw_chunks = []
        self.chunk_helper(raw_chunks)

        chunks = []
        p = 0
        for label, text_list in raw_chunks:
            if label.endswith("'"):
                label = label[:-1]
            chunks.append((label, p, p + len(text_list), text_list))
            p += len(text_list)

        return chunks


    def chunk_helper(self, chunks):

        children_status = [isinstance(child, LeafTreebankNode) for child in self.children]

        if all(children_status):
            chunks.append((self.label, [child.word for child in self.children]))
        elif any(children_status):
            char_list = []

            for child in self.children:
                if isinstance(child, InternalTreebankNode):
                    char_list += child.get_word_list()
                else:
                    char_list.append(child.word)


            chunk = (self.label, char_list)
            chunks.append(chunk)
        else:
            for child in self.children:
                if isinstance(child, InternalTreebankNode):
                    child.chunk_helper(chunks)


    def get_word_list(self):
        word_list = []
        for child in self.children:
            if isinstance(child, InternalTreebankNode):
                word_list += child.get_word_list()
            else:
                word_list += [child.word]
        return word_list

    def linearize(self):
        return "({} {})".format(
            self.label, " ".join(child.linearize() for child in self.children))

    def leaves(self):
        for child in self.children:
            yield from child.leaves()

    def convert(self, index=0):
        tree = self
        sublabels = [self.label]

        while len(tree.children) == 1 and isinstance(tree.children[0], InternalTreebankNode):
            tree = tree.children[0]
            sublabels.append(tree.label)

        children = []
        for child in tree.children:
            children.append(child.convert(index=index))
            index = children[-1].right

        return InternalParseNode(tuple(sublabels), children)



class InternalTreebankChunkNode(InternalTreebankNode):
    def __init__(self, label, children):
        super(InternalTreebankChunkNode, self).__init__(label, children)
        self.is_chunk_node = True

    def convert(self, index=0):
        tree = self
        sublabels = [self.label]

        while len(tree.children) == 1 and isinstance(tree.children[0], InternalTreebankNode):
            tree = tree.children[0]
            sublabels.append(tree.label)

        children = []
        for child in tree.children:
            children.append(child.convert(index=index))
            index = children[-1].right

        return InternalParseChunkNode(tuple(sublabels), children)


class LeafTreebankNode(TreebankNode):
    def __init__(self, tag, word):
        assert isinstance(tag, str)
        self.tag = tag

        assert isinstance(word, str)
        self.word = word

    def linearize(self):
        return "({} {})".format(self.tag, self.word)

    def leaves(self):
        yield self

    def convert(self, index=0):
        return LeafParseNode(index, self.tag, self.word)



class InternalUncompletedTreebankNode(TreebankNode):
    def __init__(self, label, chunkleaves, chunks_in_scope, latent):
        assert isinstance(label, str)
        self.label = label
        self.latent = latent
        #assert isinstance(children, collections.abc.Sequence)
        #assert all(isinstance(child, TreebankNode) for child in children)
        #assert children
        self.children = () #tuple(children)
        self.chunkleaves = chunkleaves
        self.chunks_in_scope = chunks_in_scope


    def linearize(self):

        #chunks_str_list = [ '(' + label + ' ' + ''.join( '(XX ' + item + ')' for item in text) + ')' for label, s, e, text in self.chunks_in_scope]
        return "({} leaves: {})".format(self.label, " ".join(leaf.linearize() for leaf in self.chunkleaves))

    def leaves(self):
        return self.chunkleaves

    def convert(self, index=0):
        tree = self
        sublabels = [self.label]

        # while len(tree.children) == 1 and isinstance(tree.children[0], InternalTreebankNode):
        #     tree = tree.children[0]
        #     sublabels.append(tree.label)

        #children = []
        # for child in tree.children:
        #     children.append(child.convert(index=index))
        #     index = children[-1].right
        #index = self.chunks_in_scope[0][1]
        chunkleaves = []
        for chunkleaf in self.chunkleaves:
            chunkleaves.append(chunkleaf.convert(index=index))
            index = chunkleaves[-1].right
        # for i in range(len(self.chunkleaves)):
        #     chunk = self.chunks_in_scope[i]
        #     chunkleaf = self.chunkleaves[i]
        #     chunkleaf.convert(index=chunk[1])
        #     chunkleaves.append(chunkleaf)

        return InternalUncompletedParseNode(tuple(sublabels), chunkleaves, self.chunks_in_scope, self.latent)



class ParseNode(object):
    pass

class InternalParseNode(ParseNode):
    def __init__(self, label, children):
        assert isinstance(label, tuple)
        assert all(isinstance(sublabel, str) for sublabel in label)
        assert label
        self.label = label

        assert isinstance(children, collections.abc.Sequence)
        assert all(isinstance(child, ParseNode) for child in children)
        assert children
        assert len(children) > 1 or isinstance(children[0], LeafParseNode)
        assert all(
            left.right == right.left
            for left, right in zip(children, children[1:]))
        self.children = tuple(children)

        self.left = children[0].left
        self.right = children[-1].right

    def leaves(self):
        for child in self.children:
            yield from child.leaves()

    def convert(self):
        children = [child.convert() for child in self.children]
        tree = InternalTreebankNode(self.label[-1], children)
        for sublabel in reversed(self.label[:-1]):
            tree = InternalTreebankNode(sublabel, [tree])
        return tree

    def enclosing(self, left, right):
        assert self.left <= left < right <= self.right
        for child in self.children:
            if isinstance(child, LeafParseNode):
                continue
            if child.left <= left < right <= child.right:
                return child.enclosing(left, right)
        return self

    def oracle_label(self, left, right):
        enclosing = self.enclosing(left, right)
        if enclosing.left == left and enclosing.right == right:
            return enclosing.label
        return ()

    def oracle_splits(self, left, right):
        # return [
        #     child.left
        #     for child in self.enclosing(left, right).children
        #     if left < child.left < right
        # ]
        enclosing = self.enclosing(left, right)
        return [
            child.left
            for child in enclosing.children
            if left < child.left < right
        ]
        # if isinstance(enclosing, InternalUncompletedParseNode):
        #     return [
        #         child.left
        #         for child in enclosing.chunkleaves
        #         if left < child.left < right
        #     ]
        # else:
        #     return [
        #         child.left
        #         for child in enclosing.children
        #         if left < child.left < right
        #     ]


    def oracle_splits2(self, left, right):
        # return [
        #     child.left
        #     for child in self.enclosing(left, right).children
        #     if left < child.left < right
        # ]

        enclosing = self.enclosing(left, right)
        if enclosing.left == left and enclosing.right == right:
            splits = [child.left for child in enclosing.children if not isinstance(child, LeafTreebankNode)]
            splits = splits[1:]
            return splits
        else:
            return []


        # if isinstance(self, InternalParseChunkNode):
        #     return []
        # elif isinstance(self, InternalUncompletedParseNode):
        #     return self.oracle_splits(left, right)
        # else:
        #     #enclosing = self.enclosing(left, right)
        #     if self.left == left and self.right == right:
        #         splits = [child.left for child in self.children if not isinstance(child, LeafTreebankNode)]
        #         splits = splits[1:]
        #         return splits
        #
        #
        #     for child in self.children:
        #         if not isinstance(child, LeafParseNode):
        #             if isinstance(child, InternalUncompletedParseNode):
        #                 if child.left <= left <= right <= child.right:
        #                     return child.oracle_splits(left, right)
        #             else:
        #                 if child.left == left and child.right == right:
        #                     return child.oracle_splits2(left, right)
        #
        #     return []



class InternalParseChunkNode(InternalParseNode):
    def __init__(self, label, children):
        super(InternalParseChunkNode, self).__init__(label, children)
        self.is_chunk_node = True
        self._chunknode = None

    def convert(self):
        children = [child.convert() for child in self.children]
        tree = InternalTreebankChunkNode(self.label[-1], children)
        for sublabel in reversed(self.label[:-1]):
            tree = InternalTreebankChunkNode(sublabel, [tree])
        return tree

    def enclosing(self, left, right):
        assert self.left <= left < right <= self.right
        for child in self.children:
            if isinstance(child, LeafParseNode):
                continue
            if child.left <= left < right <= child.right:
                return child.enclosing(left, right)

        if self._chunknode is None:
            self._chunknode = InternalParseChunkNode(self.label, self.children)
            self._chunknode.children = []
        return self._chunknode

    def oracle_splits(self, left, right):
        # return [
        #     child.left
        #     for child in self.enclosing(left, right).children
        #     if left < child.left < right
        # ]
        enclosing = self.enclosing(left, right)
        return [
            child.left
            for child in enclosing.children
            if left < child.left < right
        ]


class InternalUncompletedParseNode(InternalParseNode):
    def __init__(self, label, chunkleaves, chunks_in_scope:[], latent):
        assert isinstance(label, tuple)
        assert all(isinstance(sublabel, str) for sublabel in label)
        assert label
        self.label = label
        self.latent = latent

        #assert isinstance(children, collections.abc.Sequence)
        #assert all(isinstance(child, ParseNode) for child in children)
        #assert children
        #assert len(children) > 1 or isinstance(children[0], LeafParseNode)
        # assert all(
        #     left.right == right.left
        #     for left, right in zip(children, children[1:]))
        self.children = [] #tuple(children)
        self.chunkleaves = chunkleaves

        #self.left = children[0].left
        #self.right = children[-1].right
        self.left =  chunkleaves[0].left #chunks_in_scope[0][1]
        self.right = chunkleaves[-1].right #chunks_in_scope[-1][2]
        self.chunks_in_scope = chunks_in_scope
        self.splits = [chunk[1] for chunk in self.chunks_in_scope] + [self.chunks_in_scope[-1][2]]

    def leaves(self):
        return self.chunkleaves

    def convert(self):
        # children = [child.convert() for child in self.children]
        # tree = InternalUncompletedTreebankNode(self.label[-1], children)
        # for sublabel in reversed(self.label[:-1]):
        #     tree = InternalUncompletedTreebankNode(sublabel, [tree])

        chunkleaves = [chunkleaf.convert() for chunkleaf in self.chunkleaves]
        tree = InternalUncompletedTreebankNode(self.label[-1], chunkleaves, (self.left, self.right), self.latent)
        return tree

    def enclosing(self, left, right):
        assert self.left <= left < right <= self.right
        for chunkleaf in self.chunkleaves:
            if isinstance(chunkleaf, LeafParseNode):
                continue
            if chunkleaf.left <= left < right <= chunkleaf.right:
                return chunkleaf.enclosing(left, right)

        # if left in self.splits and right in self.splits:
        #     children = [chunkleaf for chunkleaf in self.chunkleaves if left <= chunkleaf.left and chunkleaf.right <= right]
        #     # label = max([child.label for child in children],key=lambda l:self.latent.get_label_order(l[0]))
        #     # label = (self.latent.non_terminal_label(label[0]),)
        #     label = self.label
        #     return InternalParseNode(label, children)

        children = [chunkleaf for chunkleaf in self.chunkleaves if left < chunkleaf.right]
        children = [chunkleaf for chunkleaf in children if right > chunkleaf.left]

        if self.latent.non_terminal_label_mode == 0 or self.latent.non_terminal_label_mode == 3:
            label = max([child.label for child in children], key=lambda l: self.latent.get_label_order(l[0]))
            label = (self.latent.non_terminal_label(label[0]),)
        elif self.latent.non_terminal_label_mode == 1:
            label = self.label
        else: #self.latent.non_terminal_label_mode == 2:
            import random
            label_id = random.randint(1 + self.latent.label_size + 0, 1 + self.latent.label_size + self.latent.label_size - 1)
            label = self.latent.label_vocab.value(label_id)
        return InternalParseNode(label, children)

        # self.children = self.chunkleaves
        # return self

    def oracle_label(self, left, right):
        # enclosing = self.enclosing(left, right)
        # if enclosing.left == left and enclosing.right == right:
        #     return enclosing.label

        for chunk in self.chunks_in_scope:
            if chunk[1] == left and chunk[2] == right:
                return (chunk[0],)


        if left in self.splits and right in self.splits:
            return self.label

        return ()

    def oracle_splits(self, left, right):


        ret = [p for p in self.splits if  left < p and p < right]
        if len(ret) == 0:
            return [
                child.left
                for child in self.enclosing(left, right).children
                if left < child.left < right
            ]


        return ret



class LeafParseNode(ParseNode):
    def __init__(self, index, tag, word):
        assert isinstance(index, int)
        assert index >= 0
        self.left = index
        self.right = index + 1

        assert isinstance(tag, str)
        self.tag = tag

        assert isinstance(word, str)
        self.word = word

    def leaves(self):
        yield self

    def convert(self):
        return LeafTreebankNode(self.tag, self.word)


def load_trees(path, normal, strip_top=True):
    with open(path, 'r', encoding='utf-8') as infile:
        tokens = infile.read().replace("(", " ( ").replace(")", " ) ").split()

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
                        if util.is_digit(c):
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
