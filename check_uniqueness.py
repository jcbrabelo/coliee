import os
import re
import hashlib
import json
from typing import Tuple, List, Dict


def check_uniqueness(train_files_path: str, train_labels_filepath: str,
                     test_files_path: str, test_labels_filepath: str) -> None:
    def what_to_keep_and_remove(dup_files: List, labels_map: Dict) -> Tuple[str, List[str]]:
        case_to_keep = None
        cases_to_remove = []
        for dup_file in dup_files:
            filename = os.path.basename(dup_file)
            if filename in labels_map:
                print(f'dup is a query case: {dup_file}. Dups: {dup_files}')
                if not case_to_keep is None:
                    msg = f'Case to keep already set (more than one dup is a query case). Manual inspection needed. Dups: {dup_files}'
                    print(msg)
                    raise BaseException(msg)
                case_to_keep = filename
            else:
                cases_to_remove.append(filename)

        if case_to_keep is None:
            case_to_keep = cases_to_remove.pop()
        
        return case_to_keep, cases_to_remove

    def guarantee_uniqueness_for_set(files_path: str, labels_filepath: str) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        hash_map = {}
        files = os.listdir(files_path)
        for file in files:
            hash = calc_hash(files_path, file)
            if not hash in hash_map:
                hash_map[hash] = []
            hash_map[hash].append(f'{files_path}/{file}')

        with open(labels_filepath, mode='r') as f:
            labels_map= json.load(f)

        for entry in hash_map.items():
            if len(entry[1]) > 1:
                print(entry)
                dup_files = entry[1]
                noticed_to_keep, noticed_to_remove = what_to_keep_and_remove(dup_files, labels_map)
                
                for noticed_cases in labels_map.values():
                    was_removed = False
                    for rem in noticed_to_remove:
                        if rem in noticed_cases:
                            noticed_cases.remove(rem)
                            was_removed = True
                            os.remove(os.path.join(files_path, rem))
                    if was_removed and not noticed_to_keep in noticed_cases:
                        noticed_cases.append(noticed_to_keep)

        with open(f'{labels_filepath}_new.json', mode='w') as f:
            json.dump(labels_map, f)

        return hash_map, labels_map

    train_hashmap, train_labels = guarantee_uniqueness_for_set(train_files_path, train_labels_filepath)
    test_hashmap, test_labels = guarantee_uniqueness_for_set(test_files_path, test_labels_filepath)

    for (test_hash, test_files) in test_hashmap.items():
        if test_hash in train_hashmap:
            train_file = os.path.basename(train_hashmap[test_hash][0])
            for test_file in test_files:
                test_file = os.path.basename(test_file)
                if test_file in test_labels and train_file in train_labels:
                    print(f'File is query in both train and test: train:{train_file}, test: {test_file}')

def calc_hash(dir_path: str, file: str) -> str:
    regex = re.compile(r'\W')

    with open(os.path.join(dir_path, file), mode='r', encoding='utf-8') as f:
        contents = f.read()
        contents = regex.sub('', contents)
        contents = contents.lower()
        return hashlib.md5(contents.encode('utf-8')).hexdigest()
    

if __name__ == '__main__':
    check_uniqueness(
        train_files_path='/Users/e401120/Downloads/task1_train_files_2024',
        train_labels_filepath='/Users/e401120/Downloads/task1_train_labels_2024.json',
        test_files_path='/Users/jrabelo/Documents/coliee2024/task1/task1_test_files_2024/redacted',
        test_labels_filepath='/Users/jrabelo/Documents/coliee2024/task1/task1_test_files_2024/task1_test_labels_2024.json'
    )