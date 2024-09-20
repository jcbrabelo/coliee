import os
import hashlib
from typing import Dict, List, Set
import json
import shutil


def build_md5_map(input_folder: str) -> Dict[str, List[str]]:
    map = {}
    for file in os.listdir(input_folder):
        with open(os.path.join(input_folder, file), mode='r', encoding='utf-8') as f:
            md5 = hashlib.md5(f.read().encode('utf-8')).hexdigest()
            if not md5 in map:
                map[md5] = []
            map[md5].append(file)

    return map

def remove_cases(labels: Dict[str, List[str]], case_to_keep: str, cases_to_delete: Set[str]):
    for case_to_delete in cases_to_delete:
        labels.pop(case_to_delete, None)

        for query in labels:
            if case_to_delete in labels[query]:
                labels[query].remove(case_to_delete)
                labels[query].append(case_to_keep)


def remove_dups(cases_dir: str, labels_path: str, output_dir: str) -> None:
    with open(labels_path, mode='r') as f:
        labels = json.load(f)

    files_to_delete = []

    md5_map = build_md5_map(cases_dir)
    for md5 in md5_map:
        cases = md5_map[md5]
        if len(cases) > 1:
            remove_cases(labels, cases[0], cases[1:])
            files_to_delete += cases[1:]


    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for case in os.listdir(cases_dir):
        if not case in files_to_delete:
            shutil.copy(os.path.join(cases_dir, case), output_dir)

    with open(os.path.join(output_dir, 'labels.json'), mode='w') as f:
        json.dump(labels, f)


def remove_dups_from_test(training_dir: str, test_dir: str, test_labels_path: str) -> None:
    training_md5_map = build_md5_map(training_dir)
    test_md5_map = build_md5_map(test_dir)
    with open(test_labels_path, mode='r') as f:
        labels = json.load(f)

    for test_md5 in test_md5_map:
        if test_md5 in training_md5_map:
            for test_file in test_md5_map[test_md5]:
                print(f'Removing {test_file} from {test_dir}')
                os.remove(os.path.join(test_dir, test_file))
                labels.pop(test_file, None)
                for query in labels:
                    if test_file in labels[query]:
                        labels[query].remove(test_file)
                        # if len(labels[query]) == 0:
                        #     labels.pop(query)

    with open(os.path.join(test_dir, 'new_labels.json'), mode='w') as f:
        json.dump(labels, f)



if __name__ == '__main__':
    # remove_dups(
    #     cases_dir='/Users/jrabelo/Documents/coliee/task1/task1_train_files_2023',
    #     labels_path='/Users/jrabelo/Documents/coliee/task1/task1_train_labels_2023.json',
    #     output_dir='/Users/jrabelo/Documents/coliee/task1/unique_task1_train_files_2023'
    # )

    remove_dups_from_test(
        training_dir='/Users/jrabelo/Documents/coliee/task1/task1_train_files_2023', 
        test_dir='/Users/jrabelo/Documents/coliee/task1/task1_test_files_2023/redacted', 
        test_labels_path='/Users/jrabelo/Documents/coliee/task1/task1_test_files_2023/test_labels.json'
    )