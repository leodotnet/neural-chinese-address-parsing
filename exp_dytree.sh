#!/usr/bin/env bash
model="chartdyRBTC"
treetype="dytree"

for pretrain in giga
do

for dropout in 0.4 #0.1 0.2 0.3 #0.4
do

for lstmdim in 200
do

for batchsize in 1 #10 #20
do

for normal in 1
do

for RBTlabel in houseno
do
#prov #city district devzone town community road subroad roadno subroadno poi subpoi #houseno cellno floorno roomno person otherinfo assist redundant #country #


for nontlabelstyle in 0 #0 #1 3 #1 2
do

for zerocostchunk in 0 #0 1
do

log="addr_"$treetype"_"$pretrain"_"$dropout"_"$lstmdim"_"$batchsize"_"$model"_"$treetype"_"$normal"_"$RBTlabel"_"$nontlabelstyle"_"$zerocostchunk
echo $log".log"

nohup python3 src/main_dyRBT.py train  --parser-type $model --model-path-base models/$model-model --lstm-dim $lstmdim --label-hidden-dim $lstmdim --split-hidden-dim $lstmdim --pretrainemb $pretrain --batch-size $batchsize --epochs 30 --treetype $treetype --expname $log --normal $normal --checks-per-epoch 4 --RBTlabel $RBTlabel --nontlabelstyle $nontlabelstyle --dropout $dropout --zerocostchunk $zerocostchunk --loadmodel none  >> $log".log" 2>&1 &

#

done
done
done
done
done
done
done
done


