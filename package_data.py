import os
from html.parser import HTMLParser
import shutil
from random import shuffle
import re

class ColieeHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = ''
        self.style = False

    def handle_data(self, data):
        if not self.style:
            self.text += ' '+data

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ['p', 'br']:
            #self.text += '\n'
            pass
        elif tag.lower() == 'style':
            self.style = True

    def handle_endtag(self, tag):
        if tag.lower() == 'style':
            self.style = False

    def get_text(self):
        return self.text


class ColieeParagraphsHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paragraphs = []
        self.span0 = False
        self.found_parag = False
        self.parag_pat = re.compile('\\[(\\d{1,4})\\]')
        self.current_paragraph_text = ''
        self.current_paragraph_number = 0

    def handle_data(self, data):
        paragraph_number = self.parse_paragraph_number(data)
        new_parag = self.span0 and self.is_valid_paragraph(paragraph_number)
        if new_parag:
            if self.current_paragraph_number > 0:
                self.paragraphs.append((self.current_paragraph_number, self.current_paragraph_text))
            self.current_paragraph_text = ''
            self.current_paragraph_number = paragraph_number
            self.found_parag = True
        elif self.found_parag:
            self.current_paragraph_text += data

    def handle_starttag(self, tag, attrs):
        self.span0 = tag.lower() == 'span' and ('class', 'span0') in attrs

    def handle_endtag(self, tag):
        """Useless implementation because some html files don't contain <html> and </html> tags. See flush()"""
        pass
#       if tag.lower() == 'html' and len(self.current_paragraph_text) > 0:
#           self.paragraphs.append((self.current_paragraph_number, self.current_paragraph_text))

    def get_paragraphs(self):
        return self.paragraphs

    def parse_paragraph_number(self, data):
        m = self.parag_pat.match(data.strip())
        if m:
            return int(m.group(1))
        else:
            return -1

    def is_valid_paragraph(self, paragraph_number):
        return paragraph_number == self.current_paragraph_number + 1

    def flush(self):
        """Since the html files don't necessarily contain <html> and </html> tags, we don't know for sure
        when it's EOF so we can add the last paragraph. Thus, we need this 'hack' to make sure the last paragraph
        is added to the list. Any user of this class must call the flush() method before retrieving the
        paragraph list"""
        if len(self.current_paragraph_text) > 0:
            self.paragraphs.append((self.current_paragraph_number, self.current_paragraph_text))
            self.current_paragraph_text = ''
            self.current_paragraph_number = 0


class ColieeSummaryHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.summary_text = ''
        self.span = False
        self.is_summary = False

    def handle_data(self, data):
        if self.is_summary and len(data.strip()) > 0:
            self.summary_text += ' ' + data
            self.is_summary = False

        if self.span:
            self.is_summary = data.lower() == 'summary:'

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'span':
            self.span = True

    def handle_endtag(self, tag):
        if tag.lower() == 'span':
            self.span = False

    def get_summary(self):
        return self.summary_text


class ColieeFactsHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.has_fact_section = False
        self.span = False

    def handle_data(self, data):
        clean_data = data.strip()
        if self.span and len(clean_data) > 0:
            if clean_data.lower() in ('facts', 'background'):
                self.has_fact_section = True

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'span':
            self.span = True

    def handle_endtag(self, tag):
        if tag.lower() == 'span':
            self.span = False

    def has_facts(self):
        return self.has_fact_section

def prepare_ir_data(input_dir, output_dir, num_candidates_per_case=200):
    all_cases_list = os.listdir(input_dir)
    for case_folder in os.listdir(input_dir):
        cited_by_case = []
        cites_path = os.path.join(input_dir, case_folder, 'cites.txt')
        if os.path.exists(cites_path) and os.path.getsize(cites_path) > 5:
            with (open(cites_path, mode='r', encoding='utf-8')) as f:
                for line in f.readlines():
                    cited_id = line.split(',')[0]
                    if len(cited_id) < 20:
                        cited_by_case.append(cited_id)

            create_ir_case(input_dir, case_folder, output_dir, cited_by_case, num_candidates_per_case, all_cases_list)
            print('num remaining cases: ', len(all_cases_list))
            if len(all_cases_list) < num_candidates_per_case:
                print('less than 200 cases available. quitting...')
                return


def prepare_ir_data_with_index(input_dir, output_dir, num_candidates_per_case=200):
    base_cases, candidates = read_index(input_dir)

    for base_case_id in base_cases:
        cited_by_case = load_cited(os.path.join(input_dir, base_case_id))
        create_ir_case(input_dir, base_case_id, output_dir, cited_by_case, num_candidates_per_case, candidates)


def load_cited(case_dir):
    cited_by_case = []
    cites_path = os.path.join(case_dir, 'cites.txt')
    if os.path.exists(cites_path) and os.path.getsize(cites_path) > 5:
        with (open(cites_path, mode='r', encoding='utf-8')) as f:
            for line in f:
                cited_id = line.split(',')[0]
                if len(cited_id) < 20:
                    cited_by_case.append(cited_id)

    return cited_by_case


def read_index(input_dir):
    index_path = os.path.join(input_dir, 'index.txt')

    base_cases = []
    candidates = []

    with open(index_path, mode='r') as index_file:
        for line in index_file:
            parts = line.split(',')

            case_id = parts[0]
            has_contents = parts[1].strip() == '1'
            has_headnotes = parts[2].strip() == '1'
            has_cites = parts[3].strip() == '1'

            if has_cites and has_headnotes:
                base_cases.append(case_id)
            elif has_contents:
                candidates.append(case_id)

    return base_cases, candidates


def case_has_fact_section(input_dir, case_id):
    casepath = os.path.join(input_dir, case_id, 'contents.html')
    with open(casepath, mode='r', encoding='utf-8', errors='ignore') as f:
        contents = f.read()
        parser = ColieeFactsHTMLParser()
        parser.feed(contents)
        has_fact = parser.has_fact_section
        parser.close()

        return has_fact


def create_ir_case(input_dir, case_id, output_dir, cited_list, num_candidates_per_case, all_candidates):
    if len(cited_list) > 0:
        output_casepath = os.path.join(output_dir, case_id)
        os.makedirs(output_casepath)
        candidates_path = os.path.join(output_casepath, 'candidates')
        os.makedirs(candidates_path)

        if not store_case_text(input_dir, case_id, output_casepath, True) or not case_has_fact_section(input_dir, case_id):
            print('base case probably incomplete or has no explicit fact section. removing dir...')
            shutil.rmtree(output_casepath)
            return

        with (open(os.path.join(output_casepath, 'true_noticed.txt'), mode='w')) as true_noticed_file:
            for cited_id in cited_list:
                cited_src_path = os.path.join(input_dir, cited_id)
                if os.path.exists(cited_src_path):
                    #cited_txt_path = os.path.join(candidates_path, cited_id+'.txt')
                    if store_case_text(input_dir, cited_id, candidates_path, False):
                        true_noticed_file.write(cited_id+'\n')

        true_written = len(os.listdir(candidates_path))
        print('true noticed cases written: ', true_written)
        if true_written == 0:
            print('no true noticed cases found. removing dir...')
            shutil.rmtree(output_casepath)
            return

        num_false_candidates = num_candidates_per_case - true_written

        candidate_indexes = list(range(0, len(all_candidates)))
        shuffle(candidate_indexes)
        i = 0
        while num_false_candidates > 0:
            if i >= len(all_candidates):
                break
            candidate = all_candidates[candidate_indexes[i]]
            if candidate != case_id and candidate not in cited_list and not candidate.startswith('.'):
                #cand_path = os.path.join(candidates_path, candidate+'.txt')
                if store_case_text(input_dir, candidate, candidates_path, False):
                    num_false_candidates -= 1
                else:
                    print('>>> id contents could not be stored: ', candidate)

                #all_candidates.remove(candidate)

            i += 1

        print('total files in the candidates folder: ', len(os.listdir(candidates_path)))


def parse_html_folder(html_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for src_folder in os.listdir(html_folder):
        if src_folder.startswith('.'):
            continue

        print('Processing ', src_folder)
        output_file = os.path.join(output_folder, src_folder + '.txt')

        store_case_text(html_folder, src_folder, output_file)


def store_case_text(html_folder, case_folder, output_folder, is_base_case):
    content_filepath = os.path.join(html_folder, case_folder, 'contents.html')
    headnotes_filepath = os.path.join(html_folder, case_folder, 'headnotes.html')
    if os.path.exists(content_filepath) and is_valid_html(content_filepath):
        if is_base_case:
            paragraphs = extract_paragraphs(content_filepath)
            contents = ''
            for p in paragraphs:
                contents += '['+str(p[0])+'] ' + p[1]
            out_contents_file = os.path.join(output_folder, 'fact.txt')

            summary = extract_summary(content_filepath, headnotes_filepath)
            out_summary_file = os.path.join(output_folder, 'summary.txt')
            with open(out_summary_file, mode='w', encoding='utf-8') as summary_file:
                summary_file.write(summary)
        else:
            contents = extract_text(content_filepath, headnotes_filepath)
            out_contents_file = os.path.join(output_folder, case_folder + '.txt')

        with open(out_contents_file, mode='w', encoding='utf-8') as main_file:
            main_file.write(contents)

        return True
    else:
        print(content_filepath)
        return False


def extract_text(content_filepath, headnotes_filepath):
    headnotes = ''
    if os.path.exists(headnotes_filepath):
        with open(headnotes_filepath, mode='r', encoding='utf-8', errors='ignore') as head_file:
            raw_headnotes = head_file.read()
            parser = ColieeHTMLParser()
            parser.feed(raw_headnotes)
            headnotes = parser.get_text() + '\n'
            parser.close()

    contents = ''
    if os.path.exists(content_filepath):
        with open(content_filepath, mode='r', encoding='utf-8', errors='ignore') as cont_file:
            raw_content = cont_file.read()
            parser = ColieeHTMLParser()
            parser.feed(raw_content)
            contents = parser.get_text()
            parser.close()

    return headnotes + contents


def extract_paragraphs(content_filepath):
    if os.path.exists(content_filepath):
        with open(content_filepath, mode='r', encoding='utf-8', errors='ignore') as cont_file:
            raw_content = cont_file.read()
            parser = ColieeParagraphsHTMLParser()
            parser.feed(raw_content)
            parser.flush()
            paragraphs = parser.get_paragraphs()
            parser.close()
            return paragraphs

    return None


def extract_summary(content_filepath, headnotes_filepath):
    summary = ''
    if os.path.exists(headnotes_filepath):
        with open(headnotes_filepath, mode='r', encoding='utf-8', errors='ignore') as head_file:
            raw_headnotes = head_file.read()
            parser = ColieeSummaryHTMLParser()
            parser.feed(raw_headnotes)
            summary = parser.get_summary()
            parser.close()
    elif os.path.exists(content_filepath):
        with open(content_filepath, mode='r', encoding='utf-8', errors='ignore') as cont_file:
            raw_content = cont_file.read()
            parser = ColieeSummaryHTMLParser()
            parser.feed(raw_content)
            summary = parser.get_summary()
            parser.close()

    return summary


def is_valid_html(filepath):
    with open(filepath, 'r', errors='ignore') as f:
        f.seek(0, os.SEEK_END)
        f.seek(f.tell() - 10, os.SEEK_SET)
        s = f.read(10)
        s = s.strip()
        return s.endswith('>')


if __name__ == '__main__':
    prepare_ir_data_with_index('C:\\juliano\\dev\\data\\coliee2019\\data_prep\\files_merged',
                    'C:\\juliano\\dev\\data\\coliee2019\\data_prep\\ir_files_20181214-3',
                    num_candidates_per_case=200)

