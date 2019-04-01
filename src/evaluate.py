import math
import os.path
import re
import subprocess
import tempfile

import trees


class FScore(object):
    def __init__(self, recall, precision, fscore):
        self.recall = recall
        self.precision = precision
        self.fscore = fscore

    def __str__(self):
        return "(Recall={:.2f}%, Precision={:.2f}%, FScore={:.2f}%)".format(
            self.recall * 100, self.precision * 100, self.fscore * 100)

def evalb(evalb_dir, gold_trees, predicted_trees, expname = "default"):
    assert os.path.exists(evalb_dir)
    evalb_program_path = os.path.join(evalb_dir, "evalb")
    evalb_param_path = os.path.join(evalb_dir, "COLLINS.prm")
    assert os.path.exists(evalb_program_path)
    assert os.path.exists(evalb_param_path)

    assert len(gold_trees) == len(predicted_trees)
    for gold_tree, predicted_tree in zip(gold_trees, predicted_trees):
        assert isinstance(gold_tree, trees.TreebankNode)
        assert isinstance(predicted_tree, trees.TreebankNode)
        gold_leaves = list(gold_tree.leaves())
        predicted_leaves = list(predicted_tree.leaves())
        assert len(gold_leaves) == len(predicted_leaves)
        assert all(
            gold_leaf.word == predicted_leaf.word
            for gold_leaf, predicted_leaf in zip(gold_leaves, predicted_leaves))

    temp_dir = tempfile.TemporaryDirectory(prefix="evalb-")
    temp_dir = 'EVALB/'
    gold_path = os.path.join(temp_dir, expname + ".gold.txt")
    predicted_path = os.path.join(temp_dir, expname + ".predicted.txt")
    output_path = os.path.join(temp_dir, expname + ".output.txt")

    with open(gold_path, "w", encoding='utf-8') as outfile:
        for tree in gold_trees:
            outfile.write("{}\n".format(tree.linearize()))

    with open(predicted_path, "w", encoding='utf-8') as outfile:
        for tree in predicted_trees:
            outfile.write("{}\n".format(tree.linearize()))

    command = "{} -p {} {} {} > {}".format(
        evalb_program_path,
        evalb_param_path,
        gold_path,
        predicted_path,
        output_path,
    )
    subprocess.run(command, shell=True)

    fscore = FScore(math.nan, math.nan, math.nan)
    with open(output_path) as infile:
        for line in infile:
            match = re.match(r"Bracketing Recall\s+=\s+(\d+\.\d+)", line)
            if match:
                fscore.recall = float(match.group(1))
            match = re.match(r"Bracketing Precision\s+=\s+(\d+\.\d+)", line)
            if match:
                fscore.precision = float(match.group(1))
            match = re.match(r"Bracketing FMeasure\s+=\s+(\d+\.\d+)", line)
            if match:
                fscore.fscore = float(match.group(1))
                break

    success = (
        not math.isnan(fscore.fscore) or
        fscore.recall == 0.0 or
        fscore.precision == 0.0)

    if success:
        pass
        #temp_dir.cleanup()
    else:
        print("Error reading EVALB results.")
        print("Gold path: {}".format(gold_path))
        print("Predicted path: {}".format(predicted_path))
        print("Output path: {}".format(output_path))

    return fscore


def count_common_chunks(chunk1, chunk2):
    common = 0
    for c1 in chunk1:
        for c2 in chunk2:
            if c1 == c2:
                common += 1

    return common


def get_performance(match_num, gold_num, pred_num):
    p = (match_num + 0.0) / pred_num
    r = (match_num + 0.0) / gold_num

    try:
        f1 = 2 * p * r / (p + r)
    except ZeroDivisionError:
        f1 = 0.0

    return p, r, f1


def get_text_from_chunks(chunks):
    text = []
    for chunk in chunks:
        text += chunk[3]

    return text


def chunk2seq(chunks:[]):
    seq = []
    for label, start_pos, end_pos, text_list in chunks:
        seq.append('B-' + label)
        for i in range(start_pos, end_pos - 1):
            seq.append('I-' + label)

    return seq

def chunks2str(chunks):
    #print(chunks)
    return ' '.join(["({} {})".format(label, ''.join(text_list)) for label, _, _, text_list in chunks])

def eval_chunks(evalb_dir, gold_trees, predicted_trees, output_filename = 'dev.out.txt'):
    match_num = 0
    gold_num = 0
    pred_num = 0



    fout = open(output_filename, 'w', encoding='utf-8')

    invalid_predicted_tree = 0

    for gold_tree, predicted_tree in zip(gold_trees, predicted_trees):

        # print(colored(gold_tree.linearize(), 'red'))
        # print(colored(predicted_tree.linearize(), 'yellow'))

        gold_chunks = gold_tree.to_chunks()
        predict_chunks = predicted_tree.to_chunks()
        input_seq = get_text_from_chunks(gold_chunks)
        gold_seq = chunk2seq(gold_chunks)
        predict_seq = chunk2seq(predict_chunks)

        if len(gold_seq) != len(predict_seq):
            invalid_predicted_tree += 1
            # print(colored('Error:', 'red'))
            # print(input_seq)
            # exit()

        o_list = zip(input_seq, gold_seq, predict_seq)
        fout.write('\n'.join(['\t'.join(x) for x in o_list]))
        fout.write('\n\n')


        # print(colored(chunks2str(gold_chunks), 'red'))
        # print(colored(chunks2str(predict_chunks), 'yellow'))
        # print()

        match_num += count_common_chunks(gold_chunks, predict_chunks)
        gold_num += len(gold_chunks)
        pred_num += len(predict_chunks)

    fout.close()

    #p, r, f1 = get_performance(match_num, gold_num, pred_num)
    # fscore = FScore(r, p, f1)
    # print('P,R,F: [{0:.2f}, {1:.2f}, {2:.2f}]'.format(p * 100, r * 100, f1 * 100), flush=True)
    print(output_filename)

    print('invalid_predicted_tree:',invalid_predicted_tree)

    cmdline = ["perl", "conlleval.pl"]
    cmd = subprocess.Popen(cmdline, stdin=open(output_filename, 'r', encoding='utf-8'),  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = cmd.communicate()
    lines = stdout.decode("utf-8")
    print(lines)
    for line in lines.split('\n'):
        if line.startswith('accuracy'):
            #print('line:', line)
            for item in line.strip().split(';'):
                items = item.strip().split(':')
                if items[0].startswith('precision'):
                    p = float(items[1].strip()[:-1]) / 100
                elif items[0].startswith('recall'):
                    r = float(items[1].strip()[:-1]) / 100
                elif items[0].startswith('FB1'):
                    f1 = float(items[1].strip()) / 100

    fscore = FScore(r, p, f1)
    print('P,R,F: [{0:.2f}, {1:.2f}, {2:.2f}]'.format(p * 100, r * 100, f1 * 100), flush=True)
    return fscore






def eval_chunks2(evalb_dir, gold_chunks_list, pred_chunk_list, output_filename = 'dev.out.txt'):
    match_num = 0
    gold_num = 0
    pred_num = 0


    fout = open(output_filename, 'w', encoding='utf-8')

    invalid_predicted_tree = 0

    for gold_chunks, predict_chunks in zip(gold_chunks_list, pred_chunk_list):

        # print(colored(gold_tree.linearize(), 'red'))
        # print(colored(predicted_tree.linearize(), 'yellow'))

        #gold_chunks = gold_tree.to_chunks()
        #predict_chunks = predicted_tree.to_chunks()
        input_seq = get_text_from_chunks(gold_chunks)
        gold_seq = chunk2seq(gold_chunks)
        predict_seq = chunk2seq(predict_chunks)

        if len(gold_seq) != len(predict_seq):
            invalid_predicted_tree += 1
            # print(colored('Error:', 'red'))
            # print(input_seq)
            # exit()

        o_list = zip(input_seq, gold_seq, predict_seq)
        fout.write('\n'.join(['\t'.join(x) for x in o_list]))
        fout.write('\n\n')


        # print(colored(chunks2str(gold_chunks), 'red'))
        # print(colored(chunks2str(predict_chunks), 'yellow'))
        # print()

        match_num += count_common_chunks(gold_chunks, predict_chunks)
        gold_num += len(gold_chunks)
        pred_num += len(predict_chunks)

    fout.close()

    #p, r, f1 = get_performance(match_num, gold_num, pred_num)
    # fscore = FScore(r, p, f1)
    # print('P,R,F: [{0:.2f}, {1:.2f}, {2:.2f}]'.format(p * 100, r * 100, f1 * 100), flush=True)
    print(output_filename)

    print('invalid_predicted_tree:',invalid_predicted_tree)

    cmdline = ["perl", "conlleval.pl"]
    cmd = subprocess.Popen(cmdline, stdin=open(output_filename, 'r', encoding='utf-8'),  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = cmd.communicate()
    lines = stdout.decode("utf-8")
    print(lines)
    for line in lines.split('\n'):
        if line.startswith('accuracy'):
            #print('line:', line)
            for item in line.strip().split(';'):
                items = item.strip().split(':')
                if items[0].startswith('precision'):
                    p = float(items[1].strip()[:-1]) / 100
                elif items[0].startswith('recall'):
                    r = float(items[1].strip()[:-1]) / 100
                elif items[0].startswith('FB1'):
                    f1 = float(items[1].strip()) / 100

    fscore = FScore(r, p, f1)
    print('P,R,F: [{0:.2f}, {1:.2f}, {2:.2f}]'.format(p * 100, r * 100, f1 * 100), flush=True)
    return fscore
