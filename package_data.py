import os
from html.parser import HTMLParser
import shutil
from random import shuffle
import re

FULL_REF_PAT = re.compile('\\s\\d{4}\\s+[A-Z\\.]{2,8}\\s+\\d{1,4}.{0,10}para(?:graph)?s?')

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
        print('invalid path or invalid html contents for: '+content_filepath)
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


def prepare_entail_data(input_dir, task1_dir, output_dir):
    '''
    Prepares an entailment task dataset
    :param input_dir: source dir with raw (html) data containing an index file
    :param task1_dir: dir with the prepared dataset for task 1. If this parameter is set, the function will not include in the task2
    dataset a case which is a task1 base case
    :param output_dir: where the task2 dataset is going to be saved. Cases already in this output_dir will be skipped
    :return:
    '''
    entailed_cases, candidates = read_index(input_dir)
    existing_cases = os.listdir(output_dir)
    task1_cases = []
    if len(task1_dir) > 0 and os.path.exists(task1_dir):
        task1_cases = os.listdir(task1_dir)

    for entailed_case_id in entailed_cases:
        if entailed_case_id in task1_cases:
            print('skipping case used for task1: '+entailed_case_id)
            continue

        if entailed_case_id in existing_cases:
            print('skipping case already used in task2: ' + entailed_case_id)
            continue

        cited_by_case = load_cited(os.path.join(input_dir, entailed_case_id))
        create_entail_case(input_dir, entailed_case_id, output_dir, cited_by_case)


def case_has_entail_candidates(case_dir, case_id):
    content_path = os.path.join(case_dir, case_id+'.txt')
    with open(content_path, mode='r', encoding='utf-8', errors='ignore') as cont_file:
        contents = cont_file.read()

        return re.search(FULL_REF_PAT, contents) is not None


def create_entail_case(input_dir, case_id, output_dir, cited_list):
    if len(cited_list) > 0:
        output_casepath = os.path.join(output_dir, case_id)
        os.makedirs(output_casepath)
        cited_path = os.path.join(output_casepath, 'cited')
        os.makedirs(cited_path)

        if not store_case_text(input_dir, case_id, output_casepath, False):
            print('base case probably incomplete. removing dir...')
            shutil.rmtree(output_casepath)
            return

        if not case_has_entail_candidates(output_casepath, case_id):
            print('base case does not contain clear entailed sentences candidates. removing dir...')
            shutil.rmtree(output_casepath)
            return

        for cited_id in cited_list:
            cited_src_path = os.path.join(input_dir, cited_id)
            if os.path.exists(cited_src_path):
                if not store_case_text(input_dir, cited_id, cited_path, False):
                    print('could not store cited case at: '+cited_path)

        cited_written = len(os.listdir(cited_path))
        print('cited cases written: ', cited_written)
        if cited_written == 0:
            print('no cited cases were written. removing dir...')
            shutil.rmtree(output_casepath)


def is_valid_html(filepath):
    with open(filepath, 'r', errors='ignore') as f:
        f.seek(0, os.SEEK_END)
        f.seek(f.tell() - 10, os.SEEK_SET)
        s = f.read(10)
        s = s.strip()
        return s.endswith('>')


def package_task2_dataset(input_dir, output_dir):
    folders = os.listdir(input_dir)
    #os.makedirs(output_dir)
    for folder in folders:
        ent_frag_filepath = os.path.join(input_dir, folder, 'entailed_fragment.txt')
        if os.path.exists(ent_frag_filepath):
            print('copying: '+folder)
            shutil.copytree(os.path.join(input_dir, folder), os.path.join(output_dir, folder))


def package_task1_release(input_dir, output_dir, training_size):
    os.makedirs(output_dir)

    cases = os.listdir(input_dir)
    indices = list(range(0, len(cases)))
    shuffle(indices)
    train_indices = indices[:training_size]
    test_indices = indices[training_size:]

    train_cases = [cases[i] for i in train_indices]
    test_cases = [cases[i] for i in test_indices]

    package_task1_cases(input_dir, train_cases, os.path.join(output_dir, 'train'))
    package_task1_cases(input_dir, test_cases, os.path.join(output_dir, 'test'))


def package_task1_cases(input_dir, cases, output_dir):
    os.makedirs(output_dir)
    mapping_filepath = os.path.join(output_dir, 'mapping.txt')
    with open(mapping_filepath, 'w') as map_file:
        case_number = 1
        for c in cases:
            print('processing '+c)
            output_case_folder = os.path.join(output_dir, '{:03d}'.format(case_number))
            output_candidates_folder = os.path.join(output_case_folder, 'candidates')
            os.makedirs(output_candidates_folder)
            output_base_case_filepath = os.path.join(output_case_folder, 'base_case.txt')
            input_case_folder =  os.path.join(input_dir, c)
            input_base_case_filepath = os.path.join(input_case_folder, c + '_blackedout-final.txt')
            map_file.write(input_case_folder + '=' + output_case_folder + '\n')

            shutil.copy(input_base_case_filepath, output_base_case_filepath)
            input_candidates_folder = os.path.join(input_dir, c, 'candidates')
            true_noticed_filepath = os.path.join(input_dir, c, 'true_noticed.txt')
            with open(true_noticed_filepath, 'r', errors='ignore') as f:
                true_noticed_cases = f.readlines()

            dst_true_noticed_filepath = os.path.join(output_case_folder, 'noticed_cases.txt')
            with open(dst_true_noticed_filepath, 'w') as f:
                candidates_src = os.listdir(input_candidates_folder)
                cand_number = 1
                for cand in candidates_src:
                    cand_src = os.path.join(input_candidates_folder, cand)
                    cand_dst = os.path.join(output_candidates_folder, '{:03d}'.format(cand_number)+'.txt')
                    map_file.write('\t' + cand_src + '=' + cand_dst + '\n')

                    shutil.copy(cand_src, cand_dst)
                    cand_id = os.path.splitext(cand)[0]
                    if cand_id+'\n' in true_noticed_cases:
                        f.write('{:03d}'.format(cand_number)+'\n')

                    cand_number += 1

            case_number += 1


def package_task2_release(input_dir, output_dir, training_size):
    os.makedirs(output_dir)

    cases = os.listdir(input_dir)
    indices = list(range(0, len(cases)))
    shuffle(indices)
    train_indices = indices[:training_size]
    test_indices = indices[training_size:]

    train_cases = [cases[i] for i in train_indices]
    test_cases = [cases[i] for i in test_indices]

    package_task2_cases(input_dir, train_cases, os.path.join(output_dir, 'train'))
    package_task2_cases(input_dir, test_cases, os.path.join(output_dir, 'test'))


def package_task2_cases(input_dir, cases, output_dir):
    os.makedirs(output_dir)
    mapping_filepath = os.path.join(output_dir, 'mapping.txt')
    with open(mapping_filepath, 'w') as map_file:
        case_number = 1
        for c in cases:
            print('processing '+c)
            output_case_folder = os.path.join(output_dir, '{:03d}'.format(case_number))
            output_paragraphs_folder = os.path.join(output_case_folder, 'paragraphs')
            os.makedirs(output_paragraphs_folder)
            output_base_case_filepath = os.path.join(output_case_folder, 'base_case.txt')
            input_base_case_folder =  os.path.join(input_dir, c)
            input_base_case_filepath = os.path.join(input_base_case_folder, c + '_blackedout.txt')
            map_file.write(input_base_case_folder + '=' + output_case_folder + '\n')

            entailed_frag_src = os.path.join(input_base_case_folder, 'entailed_fragment.txt')
            entailed_frag_dst = os.path.join(output_case_folder, 'entailed_fragment.txt')
            shutil.copy(entailed_frag_src, entailed_frag_dst)

            shutil.copy(input_base_case_filepath, output_base_case_filepath)
            input_paragraphs_folder = get_input_paragraphs_folder(os.path.join(input_dir, c))
            src_paragraphs = os.listdir(input_paragraphs_folder)

            dst_true_entailment_filepath = os.path.join(output_case_folder, 'entailing_paragraphs.txt')
            with open(dst_true_entailment_filepath, 'w') as f:
                parag_number = 1
                for parag in src_paragraphs:
                    parag_src = os.path.join(input_paragraphs_folder, parag)
                    parag_dst = os.path.join(output_paragraphs_folder, '{:03d}'.format(parag_number)+'.txt')
                    shutil.copy(parag_src, parag_dst)
                    if 'True' in parag:
                        f.write('{:03d}'.format(parag_number)+'\n')

                    parag_number += 1

            case_number += 1


def get_input_paragraphs_folder(case_path):
    parag_folder = os.path.join(case_path, 'paragraphs')
    folders = os.listdir(parag_folder)
    if len(folders) == 1:
        return os.path.join(parag_folder, folders[0])
    else:
        return None


def create_task1_xml (input_dir):
    xml_path = os.path.join(input_dir, 'task1.xml')
    with open(xml_path, 'w') as xml:
        xml.write('<COLIEE task=\'1\'>\n')

        cases = os.listdir(input_dir)
        id = 1
        for c in cases:
            if os.path.isdir(os.path.join(input_dir, c)):
                noticed_path = os.path.join(input_dir, c, 'noticed_cases.txt')
                cases_noticed = []
                if os.path.exists(noticed_path):
                    with open(noticed_path, 'r') as noticed_file:
                        cases_noticed = noticed_file.readlines()
                        cases_noticed = list(map(lambda s: s.strip(), cases_noticed))
                xml.write('<instance id=\''+'{:03d}'.format(id)+'\'>\n')
                xml.write('\t<query>'+c+'/'+'base_case.txt</query>\n')
                xml.write('\t<candidate_cases>\n')
                for cand in range(1,201):
                    xml.write('\t\t<candidate_case id=\''+'{:03d}'.format(cand)+'\'>'+'{:03d}'.format(cand)+'.txt</candidate_case>\n')
                xml.write('\t</candidate_cases>\n')
                if len(cases_noticed)>0:
                    xml.write('\t<cases_noticed>'+','.join(cases_noticed)+'</cases_noticed>\n')
                xml.write('</instance>\n')

                id += 1

        xml.write('</COLIEE>')


def create_task2_xml (input_dir):
    xml_path = os.path.join(input_dir, 'task2.xml')
    with open(xml_path, 'w') as xml:
        xml.write('<COLIEE task=\'2\'>\n')

        cases = os.listdir(input_dir)
        id = 1
        for c in cases:
            if os.path.isdir(os.path.join(input_dir, c)):
                entailing_path = os.path.join(input_dir, c, 'entailing_paragraphs.txt')
                entailing_parags = []
                if os.path.exists(entailing_path):
                    with open(entailing_path, 'r') as entailing_file:
                        entailing_parags = entailing_file.readlines()
                        entailing_parags = list(map(lambda s: s.strip(), entailing_parags))

                xml.write('<instance id=\''+'{:03d}'.format(id)+'\'>\n')
                xml.write('\t<query>\n')
                xml.write('\t\t<base_case>'+'{:03d}'.format(id)+'/base_case.txt</base_case>\n')
                xml.write('\t\t<entailed_fragment>' + '{:03d}'.format(id) + '/entailed_fragment.txt</entailed_fragment>\n')
                xml.write('\t</query>\n')
                xml.write('\t<noticed_case>\n')
                paragraphs = os.listdir(os.path.join(input_dir, c, 'paragraphs'))
                for p in paragraphs:
                    xml.write('\t\t<paragraph id=\''+os.path.splitext(p)[0]+'\'>'+p+'</paragraph>\n')
                xml.write('\t</noticed_case>\n')
                if len(entailing_parags) > 0:
                    xml.write('\t<entailing_paragraphs>'+','.join(entailing_parags)+'</entailing_paragraphs>\n')
                xml.write('</instance>\n')

                id += 1

        xml.write('</COLIEE>')


if __name__ == '__main__':
#    prepare_ir_data_with_index('C:\\juliano\\dev\\data\\coliee2019\\data_prep\\files_merged',
#                    'C:\\juliano\\dev\\data\\coliee2019\\data_prep\\ir_files_20181214-3',
#                    num_candidates_per_case=200)

#    prepare_entail_data('C:\\juliano\\dev\\data\\coliee2019\\data_prep\\files_merged',
#                        'C:\\juliano\\dev\\data\\coliee2019\\data_prep\\IR_task1',
#                        'C:\\juliano\\dev\\data\\coliee2019\\data_prep\\IR_task2_refined_2')

#    package_task2_dataset('C:\\juliano\\dev\\data\\coliee2019\\data_prep\\IR_task2_refined_2',
#                          'C:\\juliano\\dev\\data\\coliee2019\\data_prep\\IR_task2_packaged')

    #create_task1_xml('C:\\juliano\\dev\\data\\coliee2019\\data_prep\\IR_task1_release_map\\train')
    create_task1_xml('C:\\juliano\\dev\\data\\coliee2019\\data_prep\\IR_task1_release_map\\test_with_labels')
    #create_task2_xml('C:\\juliano\\dev\\data\\coliee2019\\data_prep\\EE_task2_release_map\\train')
    #create_task2_xml('C:\\juliano\\dev\\data\\coliee2019\\data_prep\\EE_task2_release_map\\test_with_labels ')
#    package_task1_release('C:\juliano\dev\data\coliee2019\data_prep\IR_task1', 'C:\juliano\dev\data\coliee2019\data_prep\IR_task1_release_map', 285)
#    package_task2_release('C:\juliano\dev\data\coliee2019\data_prep\EE_task2', 'C:\juliano\dev\data\coliee2019\data_prep\EE_task2_release_map', 181)
