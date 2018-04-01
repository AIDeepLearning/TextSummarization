# !/usr/bin/env python
# coding: utf-8
import os
import math
import time
import json
import numpy as np
import tensorflow as tf
from preprocess.iterator import BiTextIterator
from model import Seq2SeqModel
from tqdm import tqdm
from utils import prepare_pair_batch

# Data loading parameters

tf.app.flags.DEFINE_string('source_vocabulary', 'dataset/nlpcc_bpe/vocab.json', 'Path to source vocabulary')
tf.app.flags.DEFINE_string('target_vocabulary', 'dataset/nlpcc_bpe/vocab.json', 'Path to target vocabulary')
tf.app.flags.DEFINE_string('source_train_data', 'dataset/nlpcc_bpe/articles.train.txt', 'Path to source training data')
tf.app.flags.DEFINE_string('target_train_data', 'dataset/nlpcc_bpe/summaries.train.txt',
                           'Path to target training data')
tf.app.flags.DEFINE_string('source_valid_data', 'dataset/nlpcc_bpe/articles.eval.txt',
                           'Path to source validation data')
tf.app.flags.DEFINE_string('target_valid_data', 'dataset/nlpcc_bpe/summaries.eval.txt',
                           'Path to target validation data')

# Network parameters
tf.app.flags.DEFINE_string('cell_type', 'lstm', 'RNN cell for encoder and decoder, default: lstm')
tf.app.flags.DEFINE_string('attention_type', 'bahdanau', 'Attention mechanism: (bahdanau, luong), default: bahdanau')
tf.app.flags.DEFINE_integer('hidden_units', 128, 'Number of hidden units in each layer')
tf.app.flags.DEFINE_integer('depth', 2, 'Number of layers in each encoder and decoder')
tf.app.flags.DEFINE_integer('embedding_size', 300, 'Embedding dimensions of encoder and decoder inputs')
tf.app.flags.DEFINE_integer('num_encoder_symbols', 21549, 'Source vocabulary size')
tf.app.flags.DEFINE_integer('num_decoder_symbols', 21549, 'Target vocabulary size')

tf.app.flags.DEFINE_boolean('use_residual', True, 'Use residual connection between layers')
tf.app.flags.DEFINE_boolean('attn_input_feeding', False, 'Use input feeding method in attentional decoder')
tf.app.flags.DEFINE_boolean('use_dropout', True, 'Use dropout in each rnn cell')
tf.app.flags.DEFINE_float('dropout_rate', 0.3, 'Dropout probability for input/output/state units (0.0: no dropout)')
tf.app.flags.DEFINE_string('split_sign', ' ', 'Separator of dataset')

# Training parameters
tf.app.flags.DEFINE_float('learning_rate', 0.0002, 'Learning rate')
tf.app.flags.DEFINE_float('max_gradient_norm', 1.0, 'Clip gradients to this norm')
tf.app.flags.DEFINE_integer('batch_size', 64, 'Batch size')
tf.app.flags.DEFINE_integer('max_epochs', 10000, 'Maximum # of training epochs')
tf.app.flags.DEFINE_integer('max_load_batches', 20, 'Maximum # of batches to load at one time')
tf.app.flags.DEFINE_integer('source_max_length', 1500, 'Maximum sequence length')
tf.app.flags.DEFINE_integer('target_max_length', 60, 'Maximum sequence length')
tf.app.flags.DEFINE_integer('display_freq', 5, 'Display training status every this iteration')
tf.app.flags.DEFINE_integer('save_freq', 100, 'Save model checkpoint every this iteration')
tf.app.flags.DEFINE_integer('valid_freq', 100, 'Evaluate model every this iteration: valid_data needed')
tf.app.flags.DEFINE_string('optimizer', 'adam', 'Optimizer for training: (adadelta, adam, rmsprop)')
tf.app.flags.DEFINE_string('model_dir', 'model/', 'Path to save model checkpoints')
tf.app.flags.DEFINE_string('model_name', 'summary.ckpt', 'File name used for model checkpoints')
tf.app.flags.DEFINE_boolean('shuffle_each_epoch', False, 'Shuffle training dataset for each epoch')
tf.app.flags.DEFINE_boolean('sort_by_length', False, 'Sort pre-fetched minibatches by their target sequence lengths')
tf.app.flags.DEFINE_boolean('use_fp16', False, 'Use half precision float16 instead of float32 as dtype')

# Runtime parameters
tf.app.flags.DEFINE_boolean('allow_soft_placement', True, 'Allow device soft placement')
tf.app.flags.DEFINE_boolean('log_device_placement', False, 'Log placement of ops on devices')

FLAGS = tf.app.flags.FLAGS


def create_model(session, FLAGS):
    config = FLAGS.flag_values_dict()
    model = Seq2SeqModel(config, 'train')
    
    ckpt = tf.train.get_checkpoint_state(FLAGS.model_dir)
    if ckpt and tf.train.checkpoint_exists(ckpt.model_checkpoint_path):
        print('Reloading model parameters..')
        model.restore(session, ckpt.model_checkpoint_path)
    
    else:
        if not os.path.exists(FLAGS.model_dir):
            os.makedirs(FLAGS.model_dir)
        print('Created new model parameters..')
        session.run(tf.global_variables_initializer())
    
    return model


def train():
    # Load parallel data to train
    print('Loading training data..')
    train_set = BiTextIterator(source=FLAGS.source_train_data,
                               target=FLAGS.target_train_data,
                               source_dict=FLAGS.source_vocabulary,
                               target_dict=FLAGS.target_vocabulary,
                               batch_size=FLAGS.batch_size,
                               n_words_source=FLAGS.num_encoder_symbols,
                               n_words_target=FLAGS.num_decoder_symbols,
                               sort_by_length=FLAGS.sort_by_length,
                               split_sign=FLAGS.split_sign,
                               max_length=None,
                               )
    
    if FLAGS.source_valid_data and FLAGS.target_valid_data:
        print('Loading validation data..')
        valid_set = BiTextIterator(source=FLAGS.source_valid_data,
                                   target=FLAGS.target_valid_data,
                                   source_dict=FLAGS.source_vocabulary,
                                   target_dict=FLAGS.target_vocabulary,
                                   batch_size=FLAGS.batch_size,
                                   n_words_source=FLAGS.num_encoder_symbols,
                                   n_words_target=FLAGS.num_decoder_symbols,
                                   sort_by_length=FLAGS.sort_by_length,
                                   split_sign=FLAGS.split_sign,
                                   max_length=None
                                   )
    else:
        valid_set = None
    
    # Initiate TF session
    with tf.Session(config=tf.ConfigProto(allow_soft_placement=FLAGS.allow_soft_placement,
                                          log_device_placement=FLAGS.log_device_placement,
                                          gpu_options=tf.GPUOptions(allow_growth=True))) as sess:
        
        # Create a log writer object
        log_writer = tf.summary.FileWriter(FLAGS.model_dir, graph=sess.graph)
        
        # Create a new model or reload existing checkpoint
        model = create_model(sess, FLAGS)
        
        step_time, loss = 0.0, 0.0
        words_seen, sents_seen, processed_number = 0, 0, 0
        start_time = time.time()
        
        # Training loop
        print('Training..')
        
        for epoch_idx in range(FLAGS.max_epochs):
            if model.global_epoch_step.eval() >= FLAGS.max_epochs:
                print('Training is already complete.',
                      'current epoch:{}, max epoch:{}'.format(model.global_epoch_step.eval(), FLAGS.max_epochs))
                break
            
            train_set.reset()
            
            with tqdm(total=train_set.length()) as pbar:
                
                for source_seq, target_seq in train_set.next():
                    
                    # Get a batch from training parallel data
                    source, source_len, target, target_len = prepare_pair_batch(source_seq, target_seq,
                                                                                FLAGS.source_max_length,
                                                                                FLAGS.target_max_length)
                    # print('Get Data', source.shape, target.shape, source_len.shape, target_len.shape)
                    # print('Get Data', source.shape, target.shape)
                    # print('Data', , source_len[0], target_len[0])
                    
                    processed_number += len(source_seq)
                    
                    # Execute a single training step
                    step_loss, summary = model.train(sess, encoder_inputs=source, encoder_inputs_length=source_len,
                                                     decoder_inputs=target, decoder_inputs_length=target_len)
                    
                    loss += float(step_loss) / FLAGS.display_freq
                    words_seen += float(np.sum(source_len + target_len))
                    sents_seen += float(source.shape[0])  # batch_size
                    
                    if model.global_step.eval() % FLAGS.display_freq == 0:
                        avg_perplexity = math.exp(float(loss)) if loss < 300 else float("inf")
                        
                        time_elapsed = time.time() - start_time
                        step_time = time_elapsed / FLAGS.display_freq
                        
                        words_per_sec = words_seen / time_elapsed
                        sents_per_sec = sents_seen / time_elapsed
                        
                        print('Epoch:', model.global_epoch_step.eval(), 'Step:', model.global_step.eval(),
                              'Perplexity {0:.2f}:'.format(avg_perplexity), 'Loss:', loss, 'Step-time:', step_time,
                              '{0:.2f} sents/s'.format(sents_per_sec), '{0:.2f} words/s'.format(words_per_sec))
                        
                        # print('Processed Number', processed_number)
                        
                        pbar.update(processed_number)
                        
                        loss = 0
                        words_seen = 0
                        sents_seen = 0
                        processed_number = 0
                        start_time = time.time()
                        
                        # Record training summary for the current batch
                        log_writer.add_summary(summary, model.global_step.eval())
                    
                    # Execute a validation step
                    if valid_set and model.global_step.eval() % FLAGS.valid_freq == 0:
                        print('Validation step')
                        valid_loss = 0.0
                        valid_sents_seen = 0
                        
                        valid_set.reset()
                        
                        for source_seq, target_seq in valid_set.next():
                            # Get a batch from validation parallel data
                            source, source_len, target, target_len = prepare_pair_batch(source_seq, target_seq,
                                                                                        FLAGS.source_max_length,
                                                                                        FLAGS.target_max_length)
                            
                            # Compute validation loss: average per word cross entropy loss
                            step_loss, summary = model.eval(sess, encoder_inputs=source,
                                                            encoder_inputs_length=source_len,
                                                            decoder_inputs=target, decoder_inputs_length=target_len)
                            batch_size = source.shape[0]
                            
                            valid_loss += step_loss * batch_size
                            valid_sents_seen += batch_size
                            print('{} samples seen'.format(valid_sents_seen))
                        
                        valid_loss = valid_loss / valid_sents_seen
                        print('Valid perplexity: {0:.2f}'.format(math.exp(valid_loss)), 'Loss:', valid_loss)
                    
                    # Save the model checkpoint
                    if model.global_step.eval() % FLAGS.save_freq == 0:
                        print('Saving the model..')
                        checkpoint_path = os.path.join(FLAGS.model_dir, FLAGS.model_name)
                        model.save(sess, checkpoint_path, global_step=model.global_step)
                        json.dump(model.config,
                                  open('%s-%d.json' % (checkpoint_path, model.global_step.eval()), 'w'),
                                  indent=2)
            
            # Increase the epoch index of the model
            model.global_epoch_step_op.eval()
            print('Epoch {0:} DONE'.format(model.global_epoch_step.eval()))
        
        print('Saving the last model..')
        checkpoint_path = os.path.join(FLAGS.model_dir, FLAGS.model_name)
        model.save(sess, checkpoint_path, global_step=model.global_step)
        json.dump(model.config,
                  open('%s-%d.json' % (checkpoint_path, model.global_step.eval()), 'w', encoding='utf-8'),
                  indent=2)
    
    print('Training Terminated')


def main(_):
    train()


if __name__ == '__main__':
    tf.app.run()
