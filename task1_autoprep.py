from prepare_data import find_refs
import os
from package_data import extract_text
from gui_commons import *
import dbutils as db
import case_files_utils as cfu
import json

CITATION_TAG = 'CITATION'
CANDIDATE_TAG = 'CANDIDATE'
REF_TAG = 'REFERENCE'

REMOVED_REF_TAG = 'REFERENCE_SUPPRESSED'
REMOVED_CIT_TAG = 'CITATION_SUPPRESSED'


case_gen = db.task1_generator()


def redact_citations(base_case_id, txt_contents):
    cited_cases = db.get_cited_by(base_case_id, None)

    for cited_case in cited_cases:
        print(f'Processing cited case {cited_case}')
        titles = db.get_titles(cited_case)

        for t in titles:
            print(f'Removing title {t}')
            txt_contents = txt_contents.replace(t, REMOVED_REF_TAG)

    return txt_contents


def process_task1(src_folder: str, dst_folder: str, existing_query_cases: str) -> None:
    with open(existing_query_cases, 'r') as f:
        labels = json.load(f)
    try:
        while True:
            case_id = next(case_gen)
            if case_id in labels:
                print(f'Skipping case {case_id} as it is already used')
                continue

            print('Processing case {}'.format(case_id))
            if db.has_valid_citations(case_id, 5):
                html_filepath = cfu.find_case_contents_path(case_id)
                txt_contents = cfu.get_inner_text(html_filepath)
                if len(txt_contents.strip()) > 0:
                    redacted_contents = redact_citations(case_id, txt_contents)
                    output_filepath = html_filepath.replace(src_folder, dst_folder)
                    output_filepath, _ = os.path.splitext(output_filepath)
                    output_filepath += '.txt'
                    os.makedirs(os.path.dirname(output_filepath))
                    with open(output_filepath, mode='w', encoding='utf-8', errors='ignore') as f:
                        f.write(redacted_contents)
                else:
                    print(f'Skipping case {case_id} as its contents are empty')
            else:
                print('Skipping case {} as it doesn\'t have enough valid citations'.format(case_id))

    except StopIteration:
        print("No more cases.")


if __name__ == '__main__':
    CASE_REPOSITORY_PATH = '/Users/jrabelo/Documents/coliee2020/Compass Federal Court Cases for COLIEE - 2020/HTML files'
    OUTPUT_PATH = '/Users/jrabelo/Documents/coliee2020/task1_autoprep'

    process_task1(CASE_REPOSITORY_PATH, OUTPUT_PATH)