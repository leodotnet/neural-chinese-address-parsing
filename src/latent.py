import random
#import vocabulary


ASSIST = 'assist'
REDUNDANT = 'redundant'
NO = 'no'


class latent_tree_builder:
    def __init__(self, label_vocab, RBT_order_before_label, non_terminal_label_mode = 0):
        '''
        :param label_vocab:
        :param RBT_order_before_label:
        :param non_terminal_label_mode:  0, based on label order; 1, empty label <ept>;  2, random label
        '''
        self.label_vocab = label_vocab
        if RBT_order_before_label == 'none':
            self.RBT_order_before_idx = -1
        elif RBT_order_before_label == 'start':
            self.RBT_order_before_idx = 23
        else:
            self.RBT_order_before_idx = self.get_label_order(RBT_order_before_label)
        self.non_terminal_label_mode = non_terminal_label_mode
        self.label_size = 21


    def get_label_order(self, label_str):
        if label_str.endswith("'"):
            label_str = label_str[:-1]

        label = (label_str,)
        label_order = self.label_vocab.size  - self.label_vocab.index(label)
        return label_order;


    def non_terminal_label(self, label):
        if label[-1] == "'":
            return label
        else:
            return label + "'"

    def terminal_label(self, label):
        if label[-1] == "'":
            return label[:-1]
        else:
            return label


    def get_parent_label(self, child1 : str, child2 : str, order_type = 0):
        parent = None

        # if order_type == 1:
        #     return get_parent_label_reverse(child1, child2)
        #
        # if order_type == 2:
        #     return get_parent_label_order(child1, child2)
        #
        # if order_type == 3:
        #     return get_parent_label_empty(child1, child2)
        #
        # if order_type == 4:
        #     return get_parent_label_semi(child1, child2)

        if child1.startswith(REDUNDANT) or child2.startswith(REDUNDANT):
           if child1.startswith(REDUNDANT) and child2.startswith(REDUNDANT):
               parent = self.non_terminal_label(REDUNDANT)
           elif child1.startswith(REDUNDANT):
               parent = self.non_terminal_label(child2)
           else:
               parent = self.non_terminal_label(child1)

        elif child1.startswith(ASSIST) or child2.startswith(ASSIST):
           if child1.startswith(ASSIST) and child2.startswith(ASSIST):
               parent = self.non_terminal_label(ASSIST)
           elif child1.startswith(ASSIST):
               parent = self.non_terminal_label(child2)
           else:
               parent = self.non_terminal_label(child1)


        else:

            last1_priority_id = self.get_label_order(self.terminal_label(child1))
            last2_priority_id = self.get_label_order(self.terminal_label(child2))


            if last1_priority_id >= last2_priority_id:
                parent = self.non_terminal_label(child1)
            else:
                parent = self.non_terminal_label(child2)



        return parent



    def build_latent_tree_str(self, x, chunks):

        RBT_order_before_idx = self.RBT_order_before_idx
        pos_POI = -1
        for i in range(len(chunks)):
            if chunks[i][0] == 'poi':
                pos_POI = i

        if pos_POI == -1:
            RBT_order_before_idx = 0


        idx = pos_POI
        chunk_aug = [(chunk[0], chunk[1], chunk[2],'(' + chunk[0] + ' ' + ' '.join(['(XX ' + item + ')' for item in x[chunk[1]:chunk[2]]]) + ' )') for chunk in chunks]


        def create_parent_node(left, right):
            parent_label = self.get_parent_label(left[0], right[0])
            parent_left_boundary = left[1]
            parent_right_boundary = right[2]
            parent_str = '(' + parent_label + ' ' + left[3] + ' ' + right[3] + ' )'

            parent = (parent_label, parent_left_boundary, parent_right_boundary, parent_str)
            return parent

        #Build Random Tree
        while len(chunk_aug) > 1 and idx >= 0:
            label_order =  self.get_label_order(chunk_aug[idx][0])

            options = []
            if label_order < RBT_order_before_idx:
                if idx + 1 < len(chunk_aug):
                    label_order_next = self.get_label_order(chunk_aug[idx + 1][0])
                    if label_order_next < RBT_order_before_idx:
                        options.append(idx + 1)

                if idx - 1 >= 0:
                    label_order_prev = self.get_label_order(chunk_aug[idx - 1][0])
                    if label_order_prev < RBT_order_before_idx:
                        options.append(idx - 1)

            if len(options) == 0:
                break


            if len(options) == 1:
                option = options[0]
            else:
                p = random.random()
                option = options[0 if p > 0.5 else 1]


            if option == idx - 1:
                left = chunk_aug[idx - 1]
                right = chunk_aug[idx]

                parent = create_parent_node(left, right)

                chunk_aug[idx - 1] = parent
                chunk_aug.remove(right)

                idx = idx - 1
            else:
                left = chunk_aug[idx]
                right = chunk_aug[idx + 1]

                parent = create_parent_node(left, right)

                chunk_aug[idx] = parent
                chunk_aug.remove(right)

                idx = idx


        #Build RBT tree for the rest
        while len(chunk_aug) > 1:
            idx = len(chunk_aug) - 1

            left = chunk_aug[idx - 1]
            right = chunk_aug[idx]

            parent = create_parent_node(left, right)

            chunk_aug[idx - 1] = parent
            chunk_aug.remove(right)


        return chunk_aug[0][3]

    def build_latent_tree(self, x, chunks):
        import util
        tree_str = self.build_latent_tree_str(x, chunks)
        tree = util.load_trees_from_str(tree_str, 0)
        return tree

    def build_latent_trees(self, insts):
        import util
        trees_str = ''
        for x, chunks in insts:
            tree_str = self.build_latent_tree_str(x, chunks)
            trees_str += tree_str + '\n'
        trees = util.load_trees_from_str(trees_str, 0)
        return trees




    def build_dynamicRBT_tree(self, x, chunks):

        from trees import InternalTreebankNode, LeafTreebankNode, InternalUncompletedTreebankNode, InternalParseChunkNode, InternalTreebankChunkNode
        import parse

        cut_off_point = -1
        for i in reversed(range(len(chunks))):
            label_order = self.get_label_order(chunks[i][0])
            if label_order >= self.RBT_order_before_idx:
                cut_off_point = i
                break


        #Build RBT from [0, i]

        latentscope = (chunks[cut_off_point + 1][1] if cut_off_point + 1 < len(chunks) else len(x), len(x))

        chunks_in_scope = chunks[cut_off_point+1:]
        chunks_in_scope = [(label, s, e, x[s:e]) for label, s, e in chunks_in_scope]
        if len(chunks_in_scope) > 0:
            chunkleaves = []
            for label, s, e, text in chunks_in_scope:
                leaves = []
                for ch in text:
                    leaf = LeafTreebankNode(parse.XX, ch)
                    leaves.append(leaf)

                chunk_leaf = InternalTreebankNode(label, leaves)  #InternalTreebankChunkNode
                chunkleaves.append(chunk_leaf)

            if self.non_terminal_label_mode == 0 or self.non_terminal_label_mode == 3:
                label = max([chunk[0] for chunk in chunks_in_scope], key=lambda l: self.get_label_order(l))
                label = self.non_terminal_label(label)
            elif self.non_terminal_label_mode == 1:
                label = parse.EMPTY
            else:  #self.non_terminal_label_mode == 2:
                import random
                label_id = random.randint(1 + self.latent.label_size + 0, 1 + self.latent.label_size + self.latent.label_size - 1)
                label = self.label_vocab.value(label_id)

            latent_area = [InternalUncompletedTreebankNode(label, chunkleaves, chunks_in_scope, self)]
        else:
            latent_area = []

        RBT_chunks = list(chunks[:cut_off_point+1]) + latent_area  #(parse.EMPTY, chunks[i+1][1], chunks[-1][2])

        if len(latent_area) == 0:
            label, s, e = chunks[-1]
            text = x[s:e]
            leaves = []
            for ch in text:
                leaf = LeafTreebankNode(parse.XX, ch)
                leaves.append(leaf)

            RBT_chunks[-1] = InternalTreebankNode(label, leaves)

        while len(RBT_chunks) > 1:

            second_last_chunk = RBT_chunks[-2]

            second_last_children = []
            for pos in range(second_last_chunk[1], second_last_chunk[2]):
                second_last_children.append(LeafTreebankNode(parse.XX, x[pos]))

            second_last_node = InternalTreebankNode(second_last_chunk[0], second_last_children) #InternalTreebankChunkNode

            last_node = RBT_chunks[-1]

            if self.non_terminal_label_mode == 0 or self.non_terminal_label_mode == 3:
                parent_label = self.get_parent_label(second_last_chunk[0], last_node.label)
            elif self.non_terminal_label_mode == 1:
                parent_label = parse.EMPTY
            else:  #self.non_terminal_label_mode == 2:
                import random
                label_id = random.randint(1 + self.latent.label_size + 0, 1 + self.latent.label_size + self.latent.label_size - 1)
                parent_label = self.label_vocab.value(label_id)

            parent_node = InternalTreebankNode(parent_label, [second_last_node, last_node])



            RBT_chunks[-2] = parent_node
            RBT_chunks.remove(last_node)

        tree = RBT_chunks[0]
        return x, tree, chunks, latentscope

    def build_dynamicRBT_trees(self, insts):
        trees = []
        for x, chunks in insts:
            x, tree, chunks, latentscope = self.build_dynamicRBT_tree(x, chunks)
            trees.append((x, tree, chunks, latentscope))
        return trees

def main_test():
    import util
    import vocabulary
    import parse
    label_list = util.load_label_list('data/labels.txt')
    label_vocab = vocabulary.Vocabulary()

    label_vocab.index(())


    for item in label_list:
        label_vocab.index((item,))

    for item in label_list:
        label_vocab.index((item + "'",))

    label_vocab.index((parse.EMPTY,))

    label_vocab.freeze()

    latent = latent_tree_builder(label_vocab, 'city')

    insts = util.read_chunks('data/trial.txt')


    # for k in range(3):
    #     trees = latent.build_latent_trees(insts)
    #     for tree in trees:
    #         print(tree.linearize())
    #     print()


    trees = latent.build_dynamicRBT_trees(insts)
    for x, tree, chunks, latentscope in trees:
        print(tree.linearize())
        tree = tree.convert()
        print()
        tree = tree.convert()
    print()



#main_test()