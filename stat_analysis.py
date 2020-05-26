import random
from sklearn.metrics import precision_recall_fscore_support
import xml.etree.ElementTree as ET
import os
from datetime import datetime



def generate_naive_answers(golden_labels):
    res = []
    for instance in golden_labels:
        res.append([True]*len(instance))

    return res


def load_golden(xml_filepath, task=2):
    tree = ET.parse(xml_filepath)
    root = tree.getroot()
    golden_labels = []

    if task == 2:
        entailing_paragraphs = list(root.iter('entailing_paragraphs'))
        supporting_cases = list(root.iter('supporting_case'))

        for i in range(0, len(entailing_paragraphs)):
            entail_str = entailing_paragraphs[i].text
            entail_arr = entail_str.split(',')
            paragraphs = list(supporting_cases[i].iter('paragraph'))
            print('total_parags: '+str(len(paragraphs)))

            instance_labels = [False] * len(paragraphs)
            for parag_num in entail_arr:
                instance_labels[int(parag_num)-1] = True

            #print(instance_labels)
            golden_labels.append(instance_labels)
    else:
        entries = list(root.iter('entry'))
        for i in range(0, len(entries)):
            instance_labels = [False] * 200
            noticed = entries[i].find('cases_noticed')
            noticed_arr = noticed.text.split(',')
            for noticed_item in noticed_arr:
                instance_labels[int(noticed_item)-1] = True

            golden_labels.append(instance_labels)


    print(len(golden_labels))
    return golden_labels


def create_false_labels(golden_labels):
    false_labels = []
    for instance in golden_labels:
        false_labels.append([False]*len(instance))

    return false_labels


def load_res(res_filepath, golden_labels):
    pred_labels = create_false_labels(golden_labels)

    with open(res_filepath, mode='r') as f:
        for line in f:
            parts = line.split(' ')
            instance_id = int(parts[0][parts[0].index('-')+1:])
            parag_num = int(parts[1])

            instance_labels = pred_labels[instance_id-1]
            instance_labels[parag_num-1] = True

    return pred_labels


def linearize(labels):
    res = []
    for instance in labels:
        res += instance
    return res


def random_test(res1_filepath, res2_filepath, golden_xml_filepath, task=2):
    golden_labels = load_golden(golden_xml_filepath, task)
    if len(res1_filepath) == 0:
        res1 = generate_naive_answers(golden_labels)
    else:
        res1 = load_res(res1_filepath, golden_labels)

    res2 = load_res(res2_filepath, golden_labels)

    res1 = linearize(res1)
    res2 = linearize(res2)
    golden_labels = linearize(golden_labels)

    orig_precision1, orig_recall1, orig_fscore1, _ = precision_recall_fscore_support(golden_labels, res1, labels=[True])
    orig_precision2, orig_recall2, orig_fscore2, _ = precision_recall_fscore_support(golden_labels, res2, labels=[True])

    orig_fscore_diff = orig_fscore2-orig_fscore1

    #print('number of responses to sample from: '+len(combined_res))
    results1 = []
    results2 = []

    NUM_ITERATIONS = 1048576
    #NUM_ITERATIONS = 5000
    diff_equal_higher_count = 0
    for i in range(0, NUM_ITERATIONS):
        if i % 1000 == 0:
            print('iteraction #'+str(i))

        iter_res1 = [False]*len(res1)
        iter_res2 = [False]*len(res1)

        for j in range(0, len(res1)):
            if res1[j] != res2[j]:
                if random.randint(0,1) == 0:
                    iter_res1[j] = True
                else:
                    iter_res2[j] = True

        precision1, recall1, fscore1, _ = precision_recall_fscore_support(golden_labels, iter_res1, labels=[True])
        precision2, recall2, fscore2, _ = precision_recall_fscore_support(golden_labels, iter_res2, labels=[True])

#        results1.append((precision1, recall1, fscore1))
#        results2.append((precision2, recall2, fscore2))

        fscore_diff = abs(fscore1-fscore2)
        if fscore_diff >= orig_fscore_diff:
            diff_equal_higher_count += 1

    print('diff_equal_higher_count: '+str(diff_equal_higher_count))

    dir, filename1 = os.path.split(res1_filepath)
    dir, filename2 = os.path.split(res2_filepath)

    out_filename = filename1 + '_' + filename2 + '_' + datetime.now().strftime('%Y%m%d%H%M%S%f') + '.txt'
    out_filepath = os.path.join(dir, out_filename)
    with open(out_filepath, mode='w') as fout:
        fout.write(str(diff_equal_higher_count) + '/' + str(NUM_ITERATIONS))


    #print(results1)
    #print(results2)


if __name__ == '__main__':
    ee_xml_filepath = 'C:\\juliano\\dev\\data\\coliee2018\\phase2_data_August_7\\COLIEE2018_CaseLaw_Test_Data\\gold_standard\\entailment\\ee.xml'
    ir_xml_filepath = 'C:\\juliano\\dev\\data\\coliee2018\\phase2_data_August_7\\COLIEE2018_CaseLaw_Test_Data\\gold_standard\\ir\\ir.xml'

    #golden_labels = load_golden(xml_filepath)
    #res = load_res('C:\\juliano\\dev\\data\\coliee2018\\results_submission\\entailment_res_20180824.txt', golden_labels)
    #random_test('', 'C:\\juliano\\dev\\data\\coliee2018\\results_submission\\entailment_res_20180824.txt', xml_filepath)
    random_test('',
       'C:\\juliano\\dev\\data\\coliee2018\\results_submission\\entailment_res_20180824.txt', ee_xml_filepath, 2)
    #random_test('',
    #            'C:\\juliano\\dev\\data\\coliee2018\\results_submission\\ir_res_20180825_postproc.txt', ir_xml_filepath, 1)

    #print(res)
