import argparse
import itertools
import os.path
import time

import dynet_config
#dynet_config.set(random_seed = 3986067715)
import dynet as dy

import numpy as np

import evaluate
import parse
import trees
import vocabulary

import latent
import util


def format_elapsed(start_time):
    elapsed_time = int(time.time() - start_time)
    minutes, seconds = divmod(elapsed_time, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    elapsed_string = "{}h{:02}m{:02}s".format(hours, minutes, seconds)
    if days > 0:
        elapsed_string = "{}d{}".format(days, elapsed_string)
    return elapsed_string




def run_train(args):

    if args.numpy_seed is not None:
        print("Setting numpy random seed to {}...".format(args.numpy_seed))
        np.random.seed(args.numpy_seed)


    if args.trial == 1:
        args.train_path = 'data/trial.txt'
        args.dev_path = 'data/trial.txt'
        args.test_path = 'data/trial.txt'

    # args.train_path = args.train_path.replace('[*]', args.treetype)
    # args.dev_path = args.dev_path.replace('[*]', args.treetype)
    # args.test_path = args.test_path.replace('[*]', args.treetype)

    print("Loading training trees from {}...".format(args.train_path))
    train_chunk_insts = util.read_chunks(args.train_path, args.normal)
    print("Loaded {:,} training examples.".format(len(train_chunk_insts)))

    print("Loading development trees from {}...".format(args.dev_path))
    dev_chunk_insts = util.read_chunks(args.dev_path, args.normal)
    print("Loaded {:,} development examples.".format(len(dev_chunk_insts)))

    print("Loading test trees from {}...".format(args.test_path))
    test_chunk_insts = util.read_chunks(args.test_path, args.normal)
    print("Loaded {:,} test examples.".format(len(test_chunk_insts)))

    # print("Processing trees for training...")
    # train_parse = [tree.convert() for tree in train_treebank]

    print("Constructing vocabularies...")

    tag_vocab = vocabulary.Vocabulary()
    tag_vocab.index(parse.START)
    tag_vocab.index(parse.STOP)
    tag_vocab.index(parse.XX)


    word_vocab = vocabulary.Vocabulary()
    word_vocab.index(parse.START)
    word_vocab.index(parse.STOP)
    word_vocab.index(parse.UNK)
    word_vocab.index(parse.NUM)

    for x, chunks in train_chunk_insts + dev_chunk_insts + test_chunk_insts:
        for ch in x:
            word_vocab.index(ch)

    label_vocab = vocabulary.Vocabulary()
    label_vocab.index(())


    label_list = util.load_label_list(args.labellist_path) #'data/labels.txt')
    for item in label_list:
        label_vocab.index((item, ))

    if args.nontlabelstyle != 1:
        for item in label_list:
            label_vocab.index((item + "'",))

    if args.nontlabelstyle == 1:
        label_vocab.index((parse.EMPTY,))

    tag_vocab.freeze()
    word_vocab.freeze()
    label_vocab.freeze()

    latent_tree = latent.latent_tree_builder(label_vocab, args.RBTlabel, args.nontlabelstyle)

    def print_vocabulary(name, vocab):
        special = {parse.START, parse.STOP, parse.UNK}
        print("{} ({:,}): {}".format(
            name, vocab.size,
            sorted(value for value in vocab.values if value in special) +
            sorted(value for value in vocab.values if value not in special)))

    if args.print_vocabs:
        print_vocabulary("Tag", tag_vocab)
        print_vocabulary("Word", word_vocab)
        print_vocabulary("Label", label_vocab)

    print("Initializing model...")

    pretrain = {'giga':'data/giga.vec100', 'none':'none'}
    pretrainemb = util.load_pretrain(pretrain[args.pretrainemb], args.word_embedding_dim, word_vocab)

    model = dy.ParameterCollection()
    if args.parser_type == "chartdyRBTC":
        parser = parse.ChartDynamicRBTConstraintParser(
            model,
            tag_vocab,
            word_vocab,
            label_vocab,
            args.tag_embedding_dim,
            args.word_embedding_dim,
            args.lstm_layers,
            args.lstm_dim,
            args.label_hidden_dim,
            args.dropout,
            (args.pretrainemb, pretrainemb),
            args.chunkencoding,
            args.trainc == 1,
            True,
            (args.zerocostchunk == 1),
        )


    else:
        print('Model is not valid!')
        exit()

    if args.loadmodel != 'none':
        tmp = dy.load(args.loadmodel, model)
        parser = tmp[0]
        print('Model is loaded from ', args.loadmodel)

    trainer = dy.AdamTrainer(model)

    total_processed = 0
    current_processed = 0
    check_every = len(train_chunk_insts) / args.checks_per_epoch
    best_dev_fscore = -np.inf
    best_dev_model_path = None

    start_time = time.time()

    def check_dev():
        nonlocal best_dev_fscore
        nonlocal best_dev_model_path

        dev_start_time = time.time()

        dev_predicted = []
        #dev_gold = []

        #dev_gold = latent_tree.build_latent_trees(dev_chunk_insts)
        dev_gold = []
        for inst in dev_chunk_insts:
            chunks = util.inst2chunks(inst)
            dev_gold.append(chunks)

        for x, chunks in dev_chunk_insts:
            dy.renew_cg()
            #sentence = [(leaf.tag, leaf.word) for leaf in tree.leaves()]
            sentence = [(parse.XX, ch) for ch in x]
            predicted, _ = parser.parse(sentence)
            dev_predicted.append(predicted.convert().to_chunks())


        #dev_fscore = evaluate.evalb(args.evalb_dir, dev_gold, dev_predicted, args.expname + '.dev.') #evalb
        dev_fscore = evaluate.eval_chunks2(args.evalb_dir, dev_gold, dev_predicted, output_filename=args.expname + '.dev.txt')  # evalb


        print(
            "dev-fscore {} "
            "dev-elapsed {} "
            "total-elapsed {}".format(
                dev_fscore,
                format_elapsed(dev_start_time),
                format_elapsed(start_time),
            )
        )


        if dev_fscore.fscore > best_dev_fscore:
            if best_dev_model_path is not None:
                for ext in [".data", ".meta"]:
                    path = best_dev_model_path + ext
                    if os.path.exists(path):
                        print("Removing previous model file {}...".format(path))
                        os.remove(path)

            best_dev_fscore = dev_fscore.fscore
            best_dev_model_path = "{}_dev={:.2f}".format(args.model_path_base + "_" + args.expname, dev_fscore.fscore)
            print("Saving new best model to {}...".format(best_dev_model_path))
            dy.save(best_dev_model_path, [parser])

            test_start_time = time.time()
            test_predicted = []
            #test_gold = latent_tree.build_latent_trees(test_chunk_insts)
            test_gold = []
            for inst in test_chunk_insts:
                chunks = util.inst2chunks(inst)
                test_gold.append(chunks)

            ftreelog = open(args.expname + '.test.predtree.txt', 'w', encoding='utf-8')

            for x, chunks in test_chunk_insts:
                dy.renew_cg()
                #sentence = [(leaf.tag, leaf.word) for leaf in tree.leaves()]
                sentence = [(parse.XX, ch) for ch in x]
                predicted, _ = parser.parse(sentence)
                pred_tree = predicted.convert()
                ftreelog.write(pred_tree.linearize() + '\n')
                test_predicted.append(pred_tree.to_chunks())



            ftreelog.close()

            #test_fscore = evaluate.evalb(args.evalb_dir, test_chunk_insts, test_predicted, args.expname + '.test.')
            test_fscore = evaluate.eval_chunks2(args.evalb_dir, test_gold, test_predicted, output_filename=args.expname + '.test.txt')  # evalb

            print(
                "epoch {:,} "
                "test-fscore {} "
                "test-elapsed {} "
                "total-elapsed {}".format(
                    epoch,
                    test_fscore,
                    format_elapsed(test_start_time),
                    format_elapsed(start_time),
                )
            )


    train_trees = latent_tree.build_dynamicRBT_trees(train_chunk_insts)
    train_trees = [(x, tree.convert(), chunks, latentscope) for x, tree, chunks, latentscope in train_trees]

    for epoch in itertools.count(start=1):
        if args.epochs is not None and epoch > args.epochs:
            break

        np.random.shuffle(train_chunk_insts)
        epoch_start_time = time.time()

        for start_index in range(0, len(train_chunk_insts), args.batch_size):
            dy.renew_cg()
            batch_losses = []


            for x, tree, chunks, latentscope in train_trees[start_index:start_index + args.batch_size]:

                discard = False
                for chunk in chunks:
                    length = chunk[2] - chunk[1]
                    if length > args.maxllimit:
                        discard = True
                        break

                if discard:
                    continue
                    print('discard')


                sentence = [(parse.XX, ch) for ch in x]
                if args.parser_type == "top-down":
                    _, loss = parser.parse(sentence, tree, args.explore)
                else:
                    _, loss = parser.parse(sentence, tree, chunks, latentscope)
                batch_losses.append(loss)
                total_processed += 1
                current_processed += 1


            batch_loss = dy.average(batch_losses)
            batch_loss_value = batch_loss.scalar_value()
            batch_loss.backward()
            trainer.update()

            print(
                "Epoch {:,} "
                "batch {:,}/{:,} "
                "processed {:,} "
                "batch-loss {:.4f} "
                "epoch-elapsed {} "
                "total-elapsed {}".format(
                    epoch,
                    start_index // args.batch_size + 1,
                    int(np.ceil(len(train_chunk_insts) / args.batch_size)),
                    total_processed,
                    batch_loss_value,
                    format_elapsed(epoch_start_time),
                    format_elapsed(start_time),
                ), flush=True
            )

            if current_processed >= check_every:
                current_processed -= check_every
                if epoch > 7:
                    check_dev()


def run_test(args):
    #args.test_path = args.test_path.replace('[*]', args.treetype)
    print("Loading test trees from {}...".format(args.test_path))
    test_treebank = trees.load_trees(args.test_path, args.normal)
    print("Loaded {:,} test examples.".format(len(test_treebank)))

    print("Loading model from {}...".format(args.model_path_base))
    model = dy.ParameterCollection()
    [parser] = dy.load(args.model_path_base, model)

    label_vocab = vocabulary.Vocabulary()

    label_list = util.load_label_list('../data/labels.txt')
    for item in label_list:
        label_vocab.index((item, ))
    label_vocab.index((parse.EMPTY,))
    for item in label_list:
        label_vocab.index((item + "'",))

    label_vocab.freeze()
    latent_tree = latent.latent_tree_builder(label_vocab, args.RBTlabel)


    print("Parsing test sentences...")

    start_time = time.time()

    test_predicted = []
    test_gold = latent_tree.build_latent_trees(test_treebank)
    for x, chunks in test_treebank:
        dy.renew_cg()
        #sentence = [(leaf.tag, leaf.word) for leaf in tree.leaves()]
        sentence = [(parse.XX, ch) for ch in x]
        predicted, _ = parser.parse(sentence)
        test_predicted.append(predicted.convert())

    #test_fscore = evaluate.evalb(args.evalb_dir, test_treebank, test_predicted, args.expname + '.test.')
    test_fscore = evaluate.eval_chunks(args.evalb_dir, test_gold, test_predicted, output_filename=args.expname + '.finaltest.txt')  # evalb
    print(
        "test-fscore {} "
        "test-elapsed {}".format(
            test_fscore,
            format_elapsed(start_time),
        )
    )

def main():
    dynet_args = [
        "--dynet-mem",
        "--dynet-weight-decay",
        "--dynet-autobatch",
        "--dynet-gpus",
        "--dynet-gpu",
        "--dynet-devices",
        "--dynet-seed",
    ]

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    subparser = subparsers.add_parser("train")
    subparser.set_defaults(callback=run_train)
    for arg in dynet_args:
        subparser.add_argument(arg)
    subparser.add_argument("--numpy-seed", type=int)
    subparser.add_argument("--parser-type", choices=["top-down", "chartdyRBT", "chartdyRBTchunk", "chartdyRBTC", "chartdyRBTCseg"], required=True)
    subparser.add_argument("--tag-embedding-dim", type=int, default=50)
    subparser.add_argument("--word-embedding-dim", type=int, default=100)
    subparser.add_argument("--lstm-layers", type=int, default=2)
    subparser.add_argument("--lstm-dim", type=int, default=250)
    subparser.add_argument("--label-hidden-dim", type=int, default=250)
    subparser.add_argument("--split-hidden-dim", type=int, default=250)
    subparser.add_argument("--dropout", type=float, default=0.4)
    subparser.add_argument("--explore", action="store_true")
    subparser.add_argument("--model-path-base", required=True)
    subparser.add_argument("--evalb-dir", default="EVALB/")
    subparser.add_argument("--train-path", default="data/train.txt")
    subparser.add_argument("--dev-path", default="data/dev.txt")
    subparser.add_argument("--labellist-path", default="data/labels.txt")
    subparser.add_argument("--batch-size", type=int, default=10)
    subparser.add_argument("--epochs", type=int)
    subparser.add_argument("--checks-per-epoch", type=int, default=4)
    subparser.add_argument("--print-vocabs", action="store_true")
    subparser.add_argument("--test-path", default="data/test.txt")
    subparser.add_argument("--pretrainemb", default="giga")
    subparser.add_argument("--treetype", default="NRBT")
    subparser.add_argument("--expname", default="default")
    subparser.add_argument("--chunkencoding", type=int, default=1)
    subparser.add_argument("--trial", type=int, default=0)
    subparser.add_argument("--normal", type=int, default=1)
    subparser.add_argument("--RBTlabel", type=str, default="city")
    subparser.add_argument("--nontlabelstyle", type=int, default=0)
    subparser.add_argument("--zerocostchunk", type=int, default=0)
    subparser.add_argument("--loadmodel", type=str, default="none")
    subparser.add_argument("--trainc", type=int, default=1)
    subparser.add_argument("--maxllimit", type=int, default=38)


    subparser = subparsers.add_parser("test")
    subparser.set_defaults(callback=run_test)
    for arg in dynet_args:
        subparser.add_argument(arg)
    subparser.add_argument("--model-path-base", required=True)
    subparser.add_argument("--evalb-dir", default="EVALB/")
    subparser.add_argument("--treetype", default="NRBT")
    subparser.add_argument("--test-path", default="data/test.txt")
    subparser.add_argument("--expname", default="default")
    subparser.add_argument("--normal", type=int, default=1)


    args = parser.parse_args()
    args.callback(args)

if __name__ == "__main__":
    main()
