import re
import os
import json
import random
import shutil
import filecmp
import dbutils as db
import case_files_utils as cfu
from spacy.lang.en import English
from spacy.lang.en.stop_words import STOP_WORDS
import string
from nltk.corpus import words


vs_pat = re.compile('(?:(?:[A-Z]\\S+)|(?:et\\s+al\\.?))(\\s[vc]s?\\.?\\s)[A-Z]\\S+')
end_ref_pats = [re.compile('\\s\\[?\\s?\\d{4}\\s?\\]?\\s+[A-Z\\.]{2,8}\\s+[Nn]?[Oo]?\\.?\\s*\\d{1,4},?(?:\\s+a[tu]x?\\s+para(?:graph)?[es]*\\s+[\\d\\,\\-\\sand]+)?'),
                re.compile('\\[?\\d{2,4}\\]?\\s+\\d{1,2}\\s+[A-Z\\.]{2,8}\\s+\\d{1,4}'),
                re.compile('\\[?\\d{2,4}\\]?\\s+[A-Z\\.]{2,8}\\s*\\S{0,6}\\s*\\d{1,4}')]
space_pat = re.compile('\\s+')
#
ref_start_pat = re.compile('([A-Z]\\S+(?:\\s+(?:(?:[A-Z\\(]\\S+)|&|du|en|de|sur|a|dans|of|the|et|al\\.?)){0,5}\\s+[vc]s?\\.?\\s+[A-Z]\\S+)')

MAX_REF_LEN = 300
MIN_REF_LEN = 15
BLACKOUT_TAG = ' <FRAGMENT_SUPPRESSED> '
nlp = English()


def load_keywords_file(filepath):
    word_pat = re.compile(r'\b(\S+)\b')
    toks = []
    with open(filepath, mode='r', encoding='UTF-8') as f:
        contents = f.read()

        matches = re.finditer(word_pat, contents)
        for m in matches:
            toks.append(m.group(1))

    return toks


canadian_cities_provinces = load_keywords_file('canada_provinces_capitals.csv')
extra_dict = load_keywords_file('extra_dict.txt')


def blackout_refs(input_filepath, output_filepath):
    with open(input_filepath, mode='r', encoding='utf-8', errors='ignore') as fin:
        orig = fin.read()

    blacked_out = ''

    refs = find_refs(orig)

    removed_fragments = []

    last_ref_end = 0
    for (ref_start, ref_end) in refs:
        print('blacking out: ' + adjust_whitespaces(orig[ref_start:ref_end]))

        if last_ref_end == 0 or ref_start - last_ref_end > 5:
            blacked_out += orig[last_ref_end:ref_start]
            blacked_out += BLACKOUT_TAG
            removed_fragments.append(orig[ref_start:ref_end])
        else:
            print(f'joining fragments and ignoring fragment between citations: [{adjust_whitespaces(orig[last_ref_end:ref_start])}]')
            removed_fragments.append(orig[last_ref_end:ref_end])

        last_ref_end = ref_end

    blacked_out += orig[last_ref_end:]

    removed_words = get_unique_words(removed_fragments)
    ref_words = filter_ref_words(removed_words)
    print(f'words to remove: {ref_words}')
    if len(ref_words) > 0:
        remove_word_pats = build_citation_removal_patterns(ref_words)
        for pat in remove_word_pats:
            blacked_out = re.sub(pat, BLACKOUT_TAG, blacked_out)

    with open(output_filepath, mode='w', encoding='utf-8', errors='ignore') as fout:
        fout.write(blacked_out)

    return removed_fragments


def find_refs(txt):
    #vs_occurs = re.finditer(vs_pat, txt)
    vs_occurs = re.finditer(ref_start_pat, txt)
    refs = []
    for occur in vs_occurs:
        (ref_start, ref_end) = process_match(occur, txt)
        refs.append((ref_start, ref_end))

    return refs


def find_ref_start(occur, txt):
    fragment_start = max(0, occur.start(1) - 50)
    ref_start = txt.rfind('\n', fragment_start, occur.start(1))

    valid_ref = False
    if ref_start >= 0:
        print(f'Processing frag: {txt[ref_start+1:occur.start(1)]}')
        words = re.split('\\s+', txt[ref_start+1:occur.start(1)])
        valid_ref = True
        for w in words:
            if len(w) == 0:
                continue

            print(f'Processing word [{w}]')
            if (w[0] < 'A' or w[0] > 'Z') and w[0] not in ['(', '&']:
                if w not in ['et', 'al', 'al.', 'the', 'of']:
                    valid_ref = False
                    print(f'Invalid ref --->{txt[occur.start(1)-50:occur.end(1)+50]}<---: contains lower case word before vs.: {w}')
                    break
    else:
        print(f'Couldn\'t find line break within 50 chars of vs.: {txt[occur.start(1)-50:occur.end(1)+50]}')

    if valid_ref:
        return ref_start+1
    else:
        return -1





def find_ref_start_OLD(occur, txt):
    fragment_start = max(0, occur.start() - 100)
    ref_start = max(0, txt.rfind(' ', fragment_start, occur.start()))

    parts = re.split(vs_pat, txt[ref_start:occur.start()+len(vs_pat.pattern)])
    if parts[0][-1] == ')':
        fragment_start = max(0, occur.start() - 500)
        parenthesis_start = txt.rfind('(', fragment_start, occur.start())
        ref_start = txt.rfind(' ', fragment_start, parenthesis_start-1)
    elif parts[0].strip() in ('al.', 'al'):  #XXXX et al.
        ref_start = txt.rfind(' ', fragment_start, ref_start - len(parts[0]))

    return ref_start


def process_match(occur, txt):
    ref_start = occur.start(1)

    ref_end = 0

    fragment_end = min(occur.end(1) + MAX_REF_LEN, len(txt))

    for end_ref_pat in end_ref_pats:
        match = re.search(end_ref_pat, txt[occur.end(1):fragment_end])
        if match:
            if occur.end(1) + match.end() >= ref_end:
                ref_end = occur.end(1) + match.end()

    if ref_start <= 0:
        ref_start = txt.find(' ', max(0, occur.start(1) - 100), occur.start(1))
        ref_start = max(0, ref_start)
    if ref_end <= 0:
        ref_end = txt.rfind(' ', occur.end(1), min(occur.end(1) + 100, len(txt)))

    if ref_end - ref_start <= 10 or ref_end - ref_start > 400:
        print(f'suspect ref of len {ref_end - ref_start}: [{txt[ref_start:ref_end]}]')

    return ref_start, ref_end


def process_matchOLD(occur, txt):
    ref_start = find_ref_start(occur, txt)

    ref_end = 0

    fragment_end = min(occur.end(1) + MAX_REF_LEN, len(txt))

    for end_ref_pat in end_ref_pats:
        match = re.search(end_ref_pat, txt[occur.end(1):fragment_end])
        if match:
            if occur.end(1) + match.end() >= ref_end:
                ref_end = occur.end(1) + match.end()

    if ref_start <= 0:
        ref_start = txt.find(' ', max(0, occur.start(1) - 100), occur.start(1))
    if ref_end <= 0:
        ref_end = txt.rfind(' ', occur.end(1), min(occur.end(1) + 100, len(txt)))

    return ref_start, ref_end


def replace_citation_placeholder(old_placeholders, new_placeholder, input_dir):
    folders = os.listdir(input_dir)
    for folder in folders:
        print('processing  '+folder)
        folder_path = os.path.join(input_dir, folder)
        filepath = os.path.join(folder_path, folder + '_blackedout.txt')
        with open(filepath, mode='r', encoding='utf-8', errors='ignore') as fin:
            new_text = fin.read()
            for placeholder in old_placeholders:
                new_text = new_text.replace(placeholder, new_placeholder)

            out_filepath = os.path.join(folder_path, folder + '_blackedout-final.txt')
            with open(out_filepath, mode='w', encoding='utf-8', errors='ignore') as fout:
                fout.write(new_text)


def adjust_whitespaces(txt):
    return re.sub(space_pat, ' ', txt)


def prep_new_t1(input_dir, white_list, black_list, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    files = os.listdir(input_dir)
    for f in files:
        if f in black_list:
            print(f'Skipping black listed file {f}')
            continue
        if len(white_list) > 0 and f not in white_list:
            print(f'Skipping file not in while list: {f}')
            continue

        print(f'Processing file {f}')
        blackout_refs(os.path.join(input_dir, f), os.path.join(output_dir, f))


def migrate_t1_cases(train_labels_filepath, test_labels_filepath, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    mapping_filepath = os.path.join(output_dir, 'mapping_new_format.txt')
    mapping_file = open(mapping_filepath, mode='w')

    new_filenames = list(range(1, 100000))
    random.shuffle(new_filenames)

    new_labels = {}
    migrate_t1_dataset(train_labels_filepath, output_dir, True, new_filenames, mapping_file, new_labels)
    migrate_t1_dataset(test_labels_filepath, output_dir, False, new_filenames, mapping_file, new_labels)

    mapping_file.close()

    with open(os.path.join(output_dir, 'train_labels.json'), mode='w') as f:
        json.dump(new_labels, f)


def copy_to_output(src_filepath, output_dir, mapping_file, new_filenames, filesize_map, needs_redaction):
    filesize = os.path.getsize(src_filepath)
    file_contents_to_compare = src_filepath

    if needs_redaction:
        temp_filepath = os.path.join(output_dir, 'temp.txt')
        blackout_refs(src_filepath, temp_filepath)
        filesize = os.path.getsize(temp_filepath)
        file_contents_to_compare = temp_filepath

    if filesize in filesize_map:
        files = filesize_map[filesize]
        for f in files:
            if filecmp.cmp(file_contents_to_compare, f, False):
                print(f'File {src_filepath} already exists: {f}')
                mapping_file.write(f'{src_filepath}={f}\n')
                return os.path.basename(f)

    dst_filename = '{:06d}.txt'.format(new_filenames.pop())
    dst_filepath = os.path.join(output_dir, dst_filename)
    shutil.copy(file_contents_to_compare, dst_filepath)
    mapping_file.write(f'{src_filepath}={dst_filepath}\n')
    if filesize in filesize_map:
        filesize_map[filesize].append(dst_filepath)
    else:
        filesize_map[filesize] = [dst_filepath]

    return os.path.basename(dst_filename)


def get_case_contents(case_id):
    html_filepath = cfu.find_case_contents_path(case_id)
    if html_filepath is not None and os.path.exists(html_filepath) and not os.path.isdir(html_filepath):
        cited_contents = cfu.get_inner_text(html_filepath)
        return cited_contents

    return None


def create_random_unique_filenames(num_names, existing_files_dir):
    id_list = list(range(1, num_names))

    if existing_files_dir is not None:
        existing_files = os.listdir(existing_files_dir)
        for f in existing_files:
            filename, ext = os.path.splitext(f)
            try:
                file_id = int(filename)
                id_list.remove(file_id)
            except ValueError:
                print(f'Not a valid id filename: {f}')

    print(f'Size of names list: {len(id_list)}')
    random.shuffle(id_list)
    return ['{:06d}.txt'.format(file_id) for file_id in id_list]


def get_unique_words(fragments):
    # Create a Tokenizer with the default settings for English
    # including punctuation rules and exceptions
    tokenizer = nlp.tokenizer
    words = []
    for sentence in fragments:
        tokens = tokenizer(sentence)
        words += [tok.text for tok in tokens]
    return set(words)


def filter_ref_words(tokens):
    pat = re.compile(f'^[a-z]|[\\d{string.punctuation}]+')
    protected_words = set(canadian_cities_provinces
                          + extra_dict
                          + list(STOP_WORDS)
                          + words.words())
    ref_words = [w for w in tokens
                 if not pat.match(w) and len(w) > 2
                 and w.lower() not in protected_words
                 and w.capitalize() not in protected_words
                 and not w.lower().startswith('imm')]

    return ref_words


def build_citation_removal_patterns(ref_words):
    prev_words = ['in', 'at', 'citing', 'cited', 'cite', 'cites']
    following_words = ['above', 'supra']

    ref_words_disjunction = '|'.join([re.escape(w) for w in ref_words])
    following_words_disjunction = '|'.join(following_words)
    following_pat_str = f'\\b({ref_words_disjunction})\\b\\s*[\\,\\-\\;\\:]?\\s*({following_words_disjunction})'

    prev_words_disjunction = '|'.join(prev_words)
    prev_pat_str = f'\\b({prev_words_disjunction})\\s*[\\,\\-\\;\\:]?\\s*\\b({ref_words_disjunction})\\b'

    surrounded_newlines_pat_str = f'[\n\\[\\"]({ref_words_disjunction})[\n\\]\\"]'

    return [surrounded_newlines_pat_str, following_pat_str, prev_pat_str]


def generate_test_new_t1(num_cases_to_prepare, output_dir, train_dir):
    case_gen = db.task1_generator()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    txt_orig_path = os.path.join(output_dir, 'orig')
    redacted_path = os.path.join(output_dir, 'redacted')
    if not os.path.exists(txt_orig_path):
        os.makedirs(txt_orig_path)
    if not os.path.exists(redacted_path):
        os.makedirs(redacted_path)

    labels = {}
    mapping = {}

    new_filenames = create_random_unique_filenames(100000, train_dir)

    while len(labels) < num_cases_to_prepare:
        case_id = next(case_gen)
        base_contents = get_case_contents(case_id)
        if not base_contents or len(base_contents) < 100:
            print(f'Skipping case with little or empty contents: id [{case_id}]')
            continue

        print(f'Processing base case {case_id}')
        base_filename = new_filenames.pop()
        base_filepath = os.path.join(txt_orig_path, base_filename)
        with open(base_filepath, mode='w', encoding='UTF-8') as f:
            f.write(base_contents)
        redacted_base_filepath = os.path.join(redacted_path, base_filename)
        removed_fragments = blackout_refs(base_filepath, redacted_base_filepath)

        labels[base_filename] = []

        cited_cases = db.get_cited_by(case_id, None)
        for cited_id in cited_cases:
            cited_contents = get_case_contents(cited_id)
            if cited_contents is None or len(cited_contents) < 100:
                print(f'\tSkipping case with little or empty content: id [{cited_id}]')
                continue

            cited_filename = new_filenames.pop()
            cited_filepath = os.path.join(txt_orig_path, cited_filename)
            with open(cited_filepath, mode='w', encoding='UTF-8') as f:
                f.write(cited_contents)
            redacted_cited_filepath = os.path.join(redacted_path, cited_filename)
            removed_fragments = blackout_refs(cited_filepath, redacted_cited_filepath)
            removed_words = get_unique_words(removed_fragments)
            print(f'\tremoved words: {filter_ref_words(removed_words)}')

            labels[base_filename].append(cited_filename)
            mapping[cited_id] = cited_filename
            mapping[case_id] = base_filename

        if len(labels[base_filename]) == 0:
            print(f'\tNo valid cited case for base {case_id}. Removing from list...')
            labels.pop(base_filename)
            os.remove(base_filepath)
            os.remove(redacted_base_filepath)

    with open(os.path.join(output_dir, 'test_labels.json'), mode='w') as f:
        json.dump(labels, f)
    with open(os.path.join(output_dir, 'task1_mapping.txt'), mode='w') as f:
        json.dump(mapping, f)


def migrate_t1_dataset(labels_filepath, output_dir, is_train, new_filenames, mapping_file, new_labels):
    with open(labels_filepath, mode='r') as f:
        old_labels = json.load(f)

    base_dir = os.path.join(os.path.dirname(labels_filepath), '2020', 'train' if is_train else 'test')

    filesize_map = {}
    for case_id in old_labels:
        print(f'processing case [{case_id}]')
        case_path = os.path.join(base_dir, case_id)

        # copy base cases to output dir as they are already redacted
        base_case_path = os.path.join(case_path, 'base_case.txt')
        new_base_filename = copy_to_output(base_case_path, output_dir, mapping_file, new_filenames, filesize_map, False)

        # auto redact cited cases and save to output dir
        cited_dir = os.path.join(case_path, 'candidates')
        cited_cases = old_labels[case_id]
        for cited in cited_cases:
            cited_filepath = os.path.join(cited_dir, cited)
            if os.path.getsize(cited_filepath) < 100:
                print(f'removing cited file as its length is suspiciously small: {cited_filepath}')
                continue
            else:
                new_cited_filename = copy_to_output(cited_filepath, output_dir, mapping_file, new_filenames, filesize_map, True)

                if new_base_filename in new_labels:
                    new_labels[new_base_filename].append(new_cited_filename)
                else:
                    new_labels[new_base_filename] = [new_cited_filename]


if __name__ == '__main__':
    #blackout_refs('C:\\juliano\\dev\\data\\coliee2019\\data_prep\\IR_FILES_350\\r06p2yed4fporky\\fact.txt', 'c:\\juliano\\blackedout.txt')
    #blackout_refs('C:\\juliano\\dev\\data\\coliee2019\\test.txt', 'c:\\juliano\\blackedout.txt')
    #replace_citation_placeholder(['CITATION_SUPPRESSED', 'REFERENCE_SUPPRESSED'], 'FRAGMENT_SUPPRESSED', 'C:\\juliano\\dev\\data\\coliee2019\\data_prep\\IR_FILES_350')
    '''
    prep_new_t1('/Users/jrabelo/Documents/coliee2020/task1_exp_FINAL/2020/train/002/candidates',
                ["058.txt", "078.txt", "102.txt", "104.txt"],
                [],
                '/Users/jrabelo/Documents/coliee2020/test_prep_2021_newt1')
    

    migrate_t1_cases('/Users/jrabelo/Documents/coliee2020/task1_exp_FINAL/task1_train_2020_labels.json',
                     '/Users/jrabelo/Documents/coliee2020/task1_exp_FINAL/task1_test_2020_labels.json',
                     '/Users/jrabelo/Documents/coliee2021/task1_migrate_2020_FINAL')
    '''

    #blackout_refs('/Users/jrabelo/Documents/coliee2021/task1_test_sm1/orig/010757.txt',
    #              '/Users/jrabelo/Documents/coliee2021/task1_test_sm1/test.txt')
    
    cases_to_generate = 300

    # generate_test_new_t1(300,
    #                      '/Users/jrabelo/Documents/coliee2022/task1_test',
    #                      '/Users/jrabelo/Downloads/task1_train_files')
    generate_test_new_t1(
        num_cases_to_prepare=400, 
        output_dir='/Users/jrabelo/Documents/coliee2024/task1/task1_test_files_2024',
        train_dir='/Users/e401120/Downloads/task1_train_files_2024'
    )