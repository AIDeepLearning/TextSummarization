#!/usr/bin/env bash
cd ..
python3 train.py --use_length_control True --cell_type gru --attn_input_feeding True --use_bidirectional True --model_dir model/train_bpe_without_date_bigru_with_attention_input_feeding_length_control --source_vocabulary dataset/nlpcc_bpe_without_date/vocab.json --target_vocabulary dataset/nlpcc_bpe_without_date/vocab.json --source_train_data dataset/nlpcc_bpe_without_date/articles.train.txt --target_train_data dataset/nlpcc_bpe_without_date/summaries.train.txt --source_valid_data dataset/nlpcc_bpe_without_date/articles.eval.txt --target_valid_data dataset/nlpcc_bpe_without_date/summaries.eval.txt --num_encoder_symbols 21548 --num_decoder_symbols 21548 --batch_size 64 --source_max_length 1500 --target_max_length 60 --display_freq 5 --save_freq 100 --valid_freq 100