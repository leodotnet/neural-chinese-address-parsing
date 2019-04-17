# Neural Chinese Address Parsing
This page contains the code used in the work ["Neural Chinese Address Parsing"](http://statnlp.org/research/sp) published at [NAACL 2019](https://naacl2019.org/program/accepted/).


## Contents
1. [Usage](#usage)
2. [SourceCode](#sourcecode)
3. [Data](#data)
4. [Citation](#citation)
5. [Credits](#credits)


## Usage

Prerequisite: Python (3.5 or later), Dynet (2.0 or later)

Run the following command to try out the APLT(sp=7) model in the paper.
```sh
./exp_dytree.sh
```
After the training is complete, type the following command to display the result on test data. The performance outputed by conlleval.pl is shown as below.
```sh
perl conlleval.pl < addr_dytree_giga_0.4_200_1_chardyRBTC_dytree_1_houseno_0_0.test.txt
```

![alt text](log.jpg)

## SourceCode

The source code is written in Dynet, which can be found under the "src" folder.


## Data

The **data** is stored in "data" folder containing "train.txt", "dev.txt" and "test.txt". The embedding file "giga.vec100" is also located in the folder "data".

**The annotation guidelines** are in the folder ["data/anno"](https://github.com/leodotnet/neural-chinese-address-parsing/blob/master/data/anno). Both [Chinese](https://github.com/leodotnet/neural-chinese-address-parsing/blob/master/data/anno/anno-cn.md) and [English](https://github.com/leodotnet/neural-chinese-address-parsing/blob/master/data/anno/anno-en.md) versions are available.

## Citation
If you use this software for research, please cite our paper as follows:

```
@InProceedings{chineseaddressparsing19li, 
author = "Li, Hao and Lu, Wei and Xie, Pengjun and Li, Linlin", 
title = "Neural Chinese Address Parsing", 
booktitle = "Proc. of NAACL", 
year = "2019", 
}
```


## Credits
The code in this repository are based on https://github.com/mitchellstern/minimal-span-parser

Email to [hao_li@mymail.sutd.edu.sg](hao_li@mymail.sutd.edu.sg) if any inquery.
