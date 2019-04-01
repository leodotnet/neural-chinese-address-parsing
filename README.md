# Neural Chinese Address Parsing
This page contains the code used in the work "Neural Chinese Address Parsing" published at NAACL 2018.

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
After the training is complete, type the following command to display the result on test data.
```sh
perl conlleval.pl < addr_dytree_giga_0.4_200_1_chardyRBTC_dytree_1_houseno_0_0.test.txt
```


## SourceCode

The source code is written in Dynet, which can be found under the "src" folder.


## Data

The data is stored in "data" folder containing "train.txt", "dev.txt" and "test.txt". The embedding file "giga.vec100" is also located in the folder "data".

The annotation guidelines are in the folder "data/anno". Both Chinese and English versions are available.

## Citation
If you use this software for research, please cite our paper as follows:

```
@InProceedings{chineseaddressparsing19li, 
author = "Li, Hao and Lu, Wei", 
title = "Neural Chinese Address Parsing", 
booktitle = "Proc. of NAACL", 
year = "2019", 
publisher = "Association for Computational Linguistics", 
}
```


## Credits
The code in this repository are based on https://github.com/mitchellstern/minimal-span-parser

Email to hao_li@mymail.sutd.edu.sg if any inquery.
