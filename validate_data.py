import os
import dbutils as db
import shutil
import json
import re
from typing import Sequence


def remove_invalid_task1(source_dir, invalid_cases_dir):
    if not os.path.exists(invalid_cases_dir):
        os.makedirs(invalid_cases_dir)

    cases = os.listdir(source_dir)
    for base_case in cases:
        case_id = base_case.replace('.txt', ':wunu1k17')
        if not db.has_valid_citations(case_id, 1):
            print('Case with invalid citations: {}. Moving to invalid cases folder'.format(base_case))
            shutil.move(os.path.join(source_dir, base_case), os.path.join(invalid_cases_dir, base_case))
        else:
            print('Case {} has valid citations'.format(base_case))


def validate_labels_t1(labels, case_list):
    if len(labels) != len(case_list):
        print('Labels map size ({}) and number of cases in dir ({}) are different'.format(len(labels), len(case_list)))
        return

    for case_id in case_list:
        if case_id not in labels.keys():
            print('Labels map doesn\'t contain entry for case {}'.format(case_id))
            return


def get_original_case_id(exported_id, cand_filename, orig_to_exported):
    orig_id_pat = re.compile(r'/(r06\w+)[/\.]')

    if cand_filename is None:
        exported_end_string = '{}/base_case.txt'.format(exported_id)
    else:
        exported_end_string = '{}/candidates/{}'.format(exported_id, cand_filename)

    for (original_path, exported_path) in orig_to_exported.items():
        if exported_path.endswith(exported_end_string):
            orig_id = orig_id_pat.findall(original_path)
            if len(orig_id) == 1:
                return orig_id[0]
            else:
                print('invalid result retrieving original id from path {}'.format(original_path))
                return

    print('could not find original id from exported: {}'.format(exported_id))
    return None


def validate_citations(case_id, labels, orig_to_exported):
    if int(case_id) <= 346:
        print('can not validate citations from case {}'.format(case_id))
        return

    original_case_id = get_original_case_id(case_id, None, orig_to_exported)

    citations_db = db.get_cited_by(original_case_id+':wunu1k17', None)
    citations_labels = labels[case_id]
    if len(citations_db) < len(citations_labels):
        print('less citations from DB ({}) than in the labels file ({})'.format(len(citations_db), len(citations_labels)))
        return

    for citation in citations_labels:
        orig_citation_id = get_original_case_id(case_id, citation, orig_to_exported)
        if orig_citation_id is None:
            print('error! could not find original citation {} in case {}'.format(citation, case_id))

        if not orig_citation_id+':wunu1k17' not in citations_db:
            print('error! citation {} not expected'.format(orig_citation_id))


def validate_task1_case(case_root_dir, case_id, labels, orig_to_exported):
    base_case_path = os.path.join(case_root_dir, case_id, 'base_case.txt')
    candidates_path = os.path.join(case_root_dir, case_id, 'candidates')
    if not os.path.exists(base_case_path):
        print('base case file doesn\'t exist for case {}'.format(case_id))
        return

    if not os.path.exists(candidates_path):
        print('candidates folder doesn\'t exist for case {}'.format(case_id))
        return

    candidate_files = os.listdir(candidates_path)
    if not len(candidate_files) == 200:
        print('candidates folder doesn\'t contain 200 files for case {}'.format(case_id))
        return

    print('\tvalidating citations for case {}'.format(case_id))
    validate_citations(case_id, labels, orig_to_exported)


def validate_task1_package(root_dir: str, labels_filepath: str):
    with open(labels_filepath, 'r') as f:
        labels = json.load(f)
    #with open(mapping_filepath, 'r') as f:
    #    orig_to_exported = json.load(f)

    total_files_checked = 0
    for query_case in labels:
        total_files_checked += validate_task1_entry(root_dir, query_case, labels[query_case])

    print(f'Total number of files checked: {total_files_checked}')


FILE_INEXISTENT = 1
FILE_SMALL = 2

def validate_task1_entry(root_dir: str, query_case: str, noticed_cases: Sequence[str]) -> int:
    num_checked_files = 0
    print(f'Validating query case {query_case}')
    query_case_path = os.path.join(root_dir, query_case)
    errors = check_errors(query_case_path)
    if errors & FILE_INEXISTENT:
        print(f'\tQuery file {query_case} does not exist in path {root_dir}')
    elif errors & FILE_SMALL:
        print(f'\tQuery file {query_case} is too small')
    num_checked_files += 1

    for noticed_case in noticed_cases:
        noticed_case_path = os.path.join(root_dir, noticed_case)
        errors = check_errors(noticed_case_path)
        if errors & FILE_INEXISTENT:
            print(f'\tNoticed file {query_case} does not exist in path {root_dir}')
        elif errors & FILE_SMALL:
            print(f'\tNoticed file {query_case} is too small')
        num_checked_files += 1
    
    return num_checked_files


def check_errors(filepath: str) -> int:
    errors = 0
    if not os.path.exists(filepath):
        errors += FILE_INEXISTENT
    elif os.path.getsize(filepath) < 100:
        errors += FILE_SMALL
    return errors


def validate_task2_case(case_root_dir, case_id, labels, orig_to_exported):
    case_folder = os.path.join(case_root_dir, case_id)

    base_case_path = os.path.join(case_folder, 'base_case.txt')
    entailed_frag_path = os.path.join(case_folder, 'entailed_fragment.txt')
    paragraphs_path = os.path.join(case_folder, 'paragraphs')
    if not os.path.exists(base_case_path):
        print('base case file doesn\'t exist for case {}'.format(case_id))
        return

    if not os.path.exists(entailed_frag_path):
        print('entailed fragment file doesn\'t exist for case {}'.format(case_id))
        return

    if not os.path.exists(paragraphs_path):
        print('paragraphs folder doesn\'t exist for case {}'.format(case_id))
        return

    paragraph_files = os.listdir(paragraphs_path)
    if len(paragraph_files) == 0:
        print('paragraphs folder doesn\'t contain files for case {}'.format(case_id))
        return

    case_labels = labels[case_id]
    for label in case_labels:
        if label not in paragraph_files:
            print('paragraphs folder does not contain expected label file: {}'.format(labels))


def validate_task2_package(case_root_dir, labels_filepath, mapping_filepath):
    case_folders = os.listdir(case_root_dir)
    with open(labels_filepath, 'r') as f:
        labels = json.load(f)
    with open(mapping_filepath, 'r') as f:
        orig_to_exported = json.load(f)

    case_list = []
    for case_id in case_folders:
        if re.match(r'\d{3}', case_id):
            print('Validating case {}'.format(case_id))
            validate_task2_case(case_root_dir, case_id, labels, orig_to_exported)
            case_list.append(case_id)
        else:
            print('Skipping invalid folder {}'.format(case_id))

    print('validating labels file {}'.format(labels_filepath))



if __name__ == '__main__':

    validate_task1_package( '/Users/jrabelo/Documents/coliee2022/task1_test/redacted', 
                            '/Users/jrabelo/Documents/coliee2022/task1_test/test_labels.json')
    #remove_invalid_task1('/Users/jrabelo/Documents/coliee2020/task1_prep', '/Users/jrabelo/Documents/coliee2020/task1_invalid')
    '''
    validate_task1_package(case_root_dir='/Users/jrabelo/Downloads/task1/test/task1_test_2020',
                           labels_filepath='/Users/jrabelo/Downloads/task1/test/task1_test_2020_labels.json',
                           mapping_filepath='/Users/jrabelo/Downloads/task1/test/test_id_mapping.txt')

    validate_task1_package(case_root_dir='/Users/jrabelo/Downloads/task1/train/task1_train_2020',
                           labels_filepath='/Users/jrabelo/Downloads/task1/train/task1_train_2020_labels.json',
                           mapping_filepath='/Users/jrabelo/Downloads/task1/train/train_id_mapping.txt')
    

    validate_task2_package(case_root_dir='/Users/jrabelo/Downloads/task2/test/task2_test_2020',
                           labels_filepath='/Users/jrabelo/Downloads/task2/test/task2_test_labels_2020.json',
                           mapping_filepath='/Users/jrabelo/Downloads/task2/test/task2_test_id_mapping_2020.txt')

    validate_task2_package(case_root_dir='/Users/jrabelo/Downloads/task2/train/task2_train_2020',
                           labels_filepath='/Users/jrabelo/Downloads/task2/train/task2_train_labels_2020.json',
                           mapping_filepath='/Users/jrabelo/Downloads/task2/train/task2_train_id_mapping_2020.txt')

'''