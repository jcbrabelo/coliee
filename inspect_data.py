import os
import hashlib

def check_uniqueness(input_folder):
    m = hashlib.md5()
    hashmap = dict()
    for case_folder in os.listdir(input_folder):
        cand_dir = os.path.join(input_folder, case_folder, 'candidates')
        for candidate in os.listdir(cand_dir):
            cand_path = os.path.join(cand_dir, candidate)
            with (open(cand_path, mode='r', encoding='utf-8')) as f:
                m.update(f.read().encode('utf-8'))
                md5_hash = m.hexdigest()
                if hashmap.get(md5_hash) is None:
                    hashmap[md5_hash] = []
                hashmap[md5_hash].append(cand_path)

    #print(hashmap)
    for v in hashmap.values():
        if len(v) > 1:
            print (len(v))

    print('Done')

if __name__ == '__main__':
    check_uniqueness('C:\\juliano\\dev\\data\\coliee2018\\COLIEE_20180703\\IR\\data')
