import re
import os

vs_pat = re.compile('\\svs?\\.?\\s')
end_ref_pats = [re.compile('\\s\\d{4}\\s+[A-Z\\.]{2,8}\\s+\\d{1,4}(?:\\s+at\\s+para(?:graph)?s?\\s+[\\d\\,\\-\\sand]+)?'),
                re.compile('\\s\\[?\\d{4}\\]?\\s+\\d{1,2}\\s+[A-Z\\.]{2,8}\\s+\\d{1,4}')]
space_pat = re.compile('\\s+')

MAX_REF_LEN = 300
MIN_REF_LEN = 15
BLACKOUT_TAG = '<CITATION_SUPPRESSED>'


def blackout_refs(input_filepath, output_filepath):
    with open(input_filepath, mode='r', encoding='utf-8', errors='ignore') as fin:
        orig = fin.read()

    blacked_out = ''
    vs_occurs = re.finditer(vs_pat, orig)

    last_end_ref = 0
    for occur in vs_occurs:
        (start_ref, end_ref) = process_match(occur, orig)
        if (end_ref - start_ref <= MAX_REF_LEN) and (end_ref - start_ref >= MIN_REF_LEN):
            blacked_out += orig[last_end_ref:start_ref]
            blacked_out += BLACKOUT_TAG

            print('blacking out: ' + adjust_whitespaces(orig[start_ref:end_ref]))
        else:
            segment_start = max(0, occur.start() - 100)
            segment_end = min(occur.end() + 100, len(orig))
            print('skipping vs match: '+orig[segment_start:segment_end])

        last_end_ref = end_ref

    blacked_out += orig[last_end_ref:]

    with open(output_filepath, mode='w', encoding='utf-8', errors='ignore') as fout:
        fout.write(blacked_out)


def find_refs(txt):
    vs_occurs = re.finditer(vs_pat, txt)
    refs = []
    for occur in vs_occurs:
        (start_ref, end_ref) = process_match(occur, txt)
        if (end_ref - start_ref <= MAX_REF_LEN) and (end_ref - start_ref >= MIN_REF_LEN):
            refs.append((start_ref, end_ref))
        else:
            segment_start = max(0, occur.start() - 100)
            segment_end = min(occur.end() + 100, len(txt))
            refs.append((segment_start, segment_end))

    return refs

def find_ref_start(occur, txt):
    fragment_start = max(0, occur.start() - 100)
    ref_start = txt.rfind(' ', fragment_start, occur.start())

    parts = re.split(vs_pat, txt[ref_start:occur.start()+len(vs_pat.pattern)])
    if parts[0][-1] == ')':
        fragment_start = max(0, occur.start() - 500)
        parenthesis_start = txt.rfind('(', fragment_start, occur.start())
        ref_start = txt.rfind(' ', fragment_start, parenthesis_start-1)
    elif parts[0].strip() in ('al.', 'al'):  #XXXX et al.
        ref_start = txt.rfind(' ', fragment_start, ref_start - len(parts[0]))

    return ref_start


def process_match(occur, txt):
    ref_start = find_ref_start(occur, txt)

    ref_end = 0

    fragment_end = min(occur.end() + MAX_REF_LEN, len(txt))

    for end_ref_pat in end_ref_pats:
        match = re.search(end_ref_pat, txt[occur.end():fragment_end])
        if match:
            ref_end = occur.end() + match.end()
            break

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


if __name__ == '__main__':
    #blackout_refs('C:\\juliano\\dev\\data\\coliee2019\\data_prep\\IR_FILES_350\\r06p2yed4fporky\\fact.txt', 'c:\\juliano\\blackedout.txt')
    #blackout_refs('C:\\juliano\\dev\\data\\coliee2019\\test.txt', 'c:\\juliano\\blackedout.txt')
    replace_citation_placeholder(['CITATION_SUPPRESSED', 'REFERENCE_SUPPRESSED'], 'FRAGMENT_SUPPRESSED', 'C:\\juliano\\dev\\data\\coliee2019\\data_prep\\IR_FILES_350')