import dbutils as db
import random
import os
import case_files_utils as cfu
import shutil
import json
import mysql.connector
import glob


def base_case_is_blackedout(base_id):
    return True


def export_cases_t1(conn, case_ids, is_train, base_output_path, base_cases_path, coliee_edition, candidates_per_case,
                    dummy_candidates_list, initial_index):

    if is_train:
        output_path = os.path.join(base_output_path, str(coliee_edition), 'train')
    else:
        output_path = os.path.join(base_output_path, str(coliee_edition), 'test')

    golden_map = {}
    index_map = {}

    dummy_candidates_copy = list(dummy_candidates_list)

    os.makedirs(output_path)
    for case_num, base_id in enumerate(case_ids):
        filtered_base_id = cfu.filter_case_id(base_id)

        if base_case_is_blackedout(base_id):
            case_export_id_int = case_num+initial_index
            case_export_id = '{:03d}'.format(case_export_id_int)
            print('Exporting {} case. ID: {}, export ID: {}'.format('Train' if is_train else 'Test',
                  filtered_base_id, case_export_id))

            base_dir = os.path.join(output_path, case_export_id)
            os.makedirs(base_dir)
            base_case_orig_path = os.path.join(base_cases_path, filtered_base_id+'.txt')
            base_case_export_path = os.path.join(base_dir, 'base_case.txt')
            shutil.copy(base_case_orig_path, base_case_export_path)
            index_map[base_case_orig_path] = base_case_export_path

            cand_path = os.path.join(base_dir, 'candidates')
            os.makedirs(cand_path)
            cited_cases = db.get_cited_by(base_id, conn)
            candidate_ids = list(range(1, candidates_per_case + 1))
            random.shuffle(candidate_ids)
            golden_labels = []
            for cited_id in cited_cases:
                cited_export_id = '{:03d}.txt'.format(candidate_ids.pop())
                cited_output_filepath = os.path.join(cand_path, cited_export_id)
                golden_labels.append(cited_export_id)
                with open(cited_output_filepath, 'w') as f:
                    cited_original_path = cfu.find_case_contents_path(cited_id)
                    f.write(cfu.get_inner_text(cited_original_path))
                index_map[cited_original_path] = cited_output_filepath
            golden_map[case_export_id] = golden_labels

            while len(candidate_ids) > 0:
                cited_output_filepath = os.path.join(cand_path, '{:03d}.txt'.format(candidate_ids.pop()))
                with open(cited_output_filepath, 'w') as f:
                    if len(dummy_candidates_list) == 0:
                        if is_train:
                            print('>>> No more unique candidates. Restoring initial candidate list (some candidates will be repeated)')
                            dummy_candidates_list = dummy_candidates_copy
                        else:
                            print('Can\'t guarantee unique candidates in the test set. Aborting...')
                            return

                    dummy_cand_index = random.randint(0, len(dummy_candidates_list)-1)
                    dummy_cand_path = dummy_candidates_list.pop(dummy_cand_index)
                    f.write(cfu.get_inner_text(dummy_cand_path))

                    index_map[dummy_cand_path]=cited_output_filepath

    if is_train:
        golden_labels_path = os.path.join(base_output_path, 'train_golden_labels.json')
        id_map_path = os.path.join(base_output_path, 'train_id_mapping.txt')
    else:
        golden_labels_path = os.path.join(base_output_path, 'test_golden_labels.json')
        id_map_path = os.path.join(base_output_path, 'test_id_mapping.txt')

    with open(golden_labels_path, 'w') as f:
        json.dump(golden_map, f)
    with open(id_map_path, 'w') as f:
        json.dump(index_map, f)

    return case_export_id_int


def export_cases_t2(conn, dataset, is_train, base_output_path, base_cases_path, coliee_edition, initial_index):
    if len(dataset) == 0:
        return initial_index

    if is_train:
        output_path = os.path.join(base_output_path, str(coliee_edition), 'train')
    else:
        output_path = os.path.join(base_output_path, str(coliee_edition), 'test')

    golden_map = {}
    index_map = {}

    os.makedirs(output_path)
    case_export_id_int = 0
    for case_num, (base_id, noticed_id, export_id, entailed_frag, entailing_parags) in enumerate(dataset):
        filtered_base_id = cfu.filter_case_id(base_id)

        case_export_id_int = case_num+initial_index
        case_export_id = '{:03d}'.format(case_export_id_int)
        print('Exporting {} case. ID: {}, export ID: {}'.format('Train' if is_train else 'Test',
              filtered_base_id, case_export_id))

        source_dir = os.path.join(base_cases_path, filtered_base_id)
        export_dir = os.path.join(output_path, case_export_id)
        #os.makedirs(export_dir)

        print('Copying source files from {} to {}'.format(source_dir, export_dir))
        shutil.copytree(source_dir, export_dir)
        with open(os.path.join(export_dir, 'entailed_fragment.txt'), 'w', encoding='UTF-8') as f:
            f.write(entailed_frag)

        golden_map[case_export_id] = ', '.join('{:03d}.txt'.format(int(t)) for t in entailing_parags.split(', '))
        index_map[source_dir] = export_dir

    if is_train:
        golden_labels_path = os.path.join(base_output_path, 'task2_train_labels_{}.json'.format(coliee_edition))
        id_map_path = os.path.join(base_output_path, 'task2_train_id_mapping_{}.txt'.format(coliee_edition))
    else:
        golden_labels_path = os.path.join(base_output_path, 'task2_test_labels_{}.json'.format(coliee_edition))
        id_map_path = os.path.join(base_output_path, 'task2_test_id_mapping_{}.txt'.format(coliee_edition))

    with open(golden_labels_path, 'w') as f:
        json.dump(golden_map, f)
    with open(id_map_path, 'w') as f:
        json.dump(index_map, f)

    return case_export_id_int


def remove_base_from_dummy(dummy_candidates_path_list, base_ids):
    return [dummy_path for dummy_path in dummy_candidates_path_list if dummy_path.split('/')[-2]+':wunu1k17' not in base_ids]


def export_t1(output_path, base_cases_path, max_base_cases, test_portion, coliee_edition, dummy_candidates_path_list,
              initial_train_index, candidates_per_case=200):
    '''
    Exports max_base_cases (or how many cases are available) in the following folder structure:
        - [output_path]/[coliee_edition]/train: one folder per case + an XML file including the golden labels
        - [output_path]/[coliee_edition]/test: one folder per case + an XML file NOT including the golden labels
        - [output_path]/[coliee_edition]/test_with_labels.xml: the test XML file with the golden labels

    The state is saved to the db

    :param output_path: base output path
    :param base_cases_path: base path with the blacked out base files contents
    :param max_base_cases: upper limit of cases to export
    :param test_portion: if float between 0 and 1, the proportion of the set used as the test set. If integer, the
    absolute number of test cases
    :param coliee_edition: integer representing the year of the COLIEE edition
    :param dummy_candidates_path_list: list of path to directories containing the cases which are used only as dummy candidates
    :param initial_train_index: first index to output as train (usually, the last index from the previous year dataset + 1)
    :param candidates_per_case: total number of candidates per case (default: 200)

    :return:
    '''
    case_ids = db.get_prepared_t1()
    train_ids, test_ids = split_train_test(case_ids, max_base_cases, test_portion)

    print('Dataset sizes: \n\tTrain:{}\n\tTest:{}'.format(len(train_ids), len(test_ids)))

    try:
        conn = db.get_connection()
        conn.autocommit = False
        #cursor = conn.cursor()

        dummy_candidates = build_dummy_candidates_list(case_ids, dummy_candidates_path_list)

        last_train_index = export_cases_t1(conn, train_ids, True, output_path, base_cases_path, coliee_edition, candidates_per_case,
                        dummy_candidates, initial_train_index)
        export_cases_t1(conn, test_ids, False, output_path, base_cases_path, coliee_edition, candidates_per_case,
                        dummy_candidates, last_train_index+1)


        conn.commit()
    except mysql.connector.Error as error:
        print('Rolling back - failed to update. Error: {}'.format(error))
        conn.rollback()
    finally:
        if conn.is_connected():
            #cursor.close()
            conn.close()


def split_train_test(samples, max_base_cases, num_test_cases):
    random.shuffle(samples)
    if 0 < max_base_cases < len(samples):
        samples = samples[:max_base_cases]
    if num_test_cases < 1:
        num_test_cases = int(num_test_cases * len(samples))
    else:
        num_test_cases = int(num_test_cases)

    train_dataset = samples[:-num_test_cases]
    test_dataset = samples[-num_test_cases:]

    return train_dataset, test_dataset


def find_case_files(base_dir):
    subdir = '*'
    files_list = []
    while len(files_list) == 0:
        files_list = glob.glob(os.path.join(base_dir, subdir, 'r*', 'content*html'))
        subdir = subdir + '/*'

    return set(files_list)


def build_dummy_candidates_list(case_ids, dummy_candidates_path_list):
    dummy_candidates = set()
    for dummy_path in dummy_candidates_path_list:
        print('Reading dummy candidates from {}'.format(dummy_path))
        dummy_candidates = dummy_candidates | find_case_files(dummy_path)
    print('Dummy candidates size: {}'.format(len(dummy_candidates)))
    dummy_candidates = remove_base_from_dummy(dummy_candidates, case_ids)
    print('Dummy candidates size after removing base cases: {}'.format(len(dummy_candidates)))
    return list(dummy_candidates)


def export_t2(output_path,
              base_cases_path,
              max_base_cases,
              num_test_cases,
              coliee_edition,
              initial_train_index):
    case_ids = db.get_prepared_t2()
    train_sample, test_sample = split_train_test(case_ids, max_base_cases, num_test_cases)

    print('Dataset sizes: \n\tTrain:{}\n\tTest:{}'.format(len(train_sample), len(test_sample)))

    try:
        conn = db.get_connection()
        conn.autocommit = False
        #cursor = conn.cursor()

        last_train_index = export_cases_t2(conn, train_sample, True, output_path, base_cases_path, coliee_edition,
                                           initial_train_index)
        export_cases_t2(conn, test_sample, False, output_path, base_cases_path, coliee_edition,
                        last_train_index+1)

        conn.commit()
    except mysql.connector.Error as error:
        print('Rolling back - failed to update. Error: {}'.format(error))
        conn.rollback()
    finally:
        if conn.is_connected():
            #cursor.close()
            conn.close()

if __name__ == '__main__':
    '''
    export_t1(output_path='/Users/jrabelo/Documents/coliee2020/task1_exp_FINAL',
              base_cases_path='/Users/jrabelo/Documents/coliee2020/task1_prep',
              max_base_cases=0,
              test_portion=130,
              #test_portion=0.3,
              coliee_edition=2020,
              dummy_candidates_path_list=[
                  '/Users/jrabelo/Documents/coliee2020/additional_files',
                  '/Users/jrabelo/Documents/coliee2020/Compass Federal Court Cases for COLIEE - 2020/HTML files'
              ],
              initial_train_index=347,
              candidates_per_case=200)
    '''

    export_t2(
        output_path='/Users/jrabelo/Documents/coliee2024/task2_export',
        base_cases_path='/Users/jrabelo/Documents/coliee2024/task2_prep',
        max_base_cases=0,
        num_test_cases=100,
        coliee_edition=2024,
        initial_train_index=725
    )
