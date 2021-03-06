import time
from tqdm import tqdm

from preprocess.iterator import BiTextIterator, TextIterator
from train import FLAGS
from utils import prepare_pair_batch

batch_size = 6


def main():
    train_set = BiTextIterator(source='dataset/summerization_sample/articles.eval.sample.txt',
                               target='dataset/summerization_sample/summaries.eval.sample.txt',
                               source_dict='dataset/summerization_sample/vocab.json',
                               target_dict='dataset/summerization_sample/vocab.json',
                               batch_size=batch_size,
                               max_length=None,
                               n_words_source=21548,
                               n_words_target=21548,
                               sort_by_length=FLAGS.sort_by_length,
                               split_sign=FLAGS.split_sign,
                               )
    with tqdm(total=train_set.length()) as pbar:
        train_set.reset()
        processed_length = 0
        for source_seq, target_seq in train_set.next():
            processed_length += len(source_seq)
            print('Length', len(source_seq), len(target_seq), processed_length)
            time.sleep(1)
            pbar.update(len(source_seq))
            
            source, source_len, target, target_len = prepare_pair_batch(source_seq, target_seq,
                                                                        FLAGS.source_max_length,
                                                                        FLAGS.target_max_length)
            print('Get Data', source.shape, target.shape, source_len.shape, target_len.shape)
            
            # print('Source 0', list(source[0]), len(source[0]))
            # print('Source 0', list(target[0]), len(target[0]))
    
    train_set.reset()
    
    print('Reset')
    
    for source, target in train_set.next():
        print('Length', len(source), len(target))


if __name__ == '__main__':
    main()
