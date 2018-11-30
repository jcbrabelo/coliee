import os
from html.parser import HTMLParser
import shutil
from random import shuffle

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

class ColieeSummaryHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.summary_text = ''
        self.span = False
        self.is_summary = False

    def handle_data(self, data):
        if self.is_summary:
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


def create_ir_case(input_dir, case_id, output_dir, cited_list, num_candidates_per_case, all_cases_list):
    if len(cited_list) > 0:
        output_casepath = os.path.join(output_dir, case_id)
        os.makedirs(output_casepath)
        candidates_path = os.path.join(output_casepath, 'candidates')
        os.makedirs(candidates_path)

        store_case_text(input_dir, case_id, output_casepath, True)

        num_false_candidates = num_candidates_per_case

        with (open(os.path.join(output_casepath, 'true_noticed.txt'), mode='w')) as true_noticed_file:
            for cited_id in cited_list:
                cited_src_path = os.path.join(input_dir, cited_id)
                if os.path.exists(cited_src_path):
                    #cited_txt_path = os.path.join(candidates_path, cited_id+'.txt')
                    if store_case_text(input_dir, cited_id, candidates_path, False):
                        true_noticed_file.write(cited_id+'\n')
                        num_false_candidates -= 1

        true_written = len(os.listdir(candidates_path))
        print('true noticed cases written: ', true_written)
        if true_written == 0:
            print('no true noticed cases found. removing dir...')
            shutil.rmtree(output_casepath)
            return

        i = 0
        while num_false_candidates > 0:
            if i >= len(all_cases_list):
                break
            candidate = all_cases_list[i]
            if candidate != case_id and candidate not in cited_list and not candidate.startswith('.'):
                #cand_path = os.path.join(candidates_path, candidate+'.txt')
                if store_case_text(input_dir, candidate, candidates_path, False):
                    num_false_candidates -= 1
                else:
                    print('>>> id contents could not be stored: ', candidate)

                all_cases_list.remove(candidate)
            else:
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
    if os.path.exists(content_filepath):
        with open(content_filepath, mode='r', encoding='utf-8') as cont_file:
            raw_contents = cont_file.read()
            parser = ColieeHTMLParser()
            parser.feed(raw_contents)
            contents = parser.get_text()
            parser.close()

            out_contents_file = os.path.join(output_folder, case_folder + '.txt')
            if is_base_case:
                out_contents_file = os.path.join(output_folder, 'fact.txt')
                #TODO contents = get+paragraphs(contents)

            with open(out_contents_file, mode='w', encoding='utf-8') as main_file:
                main_file.write(contents)   #TODO: keep only paragraphs if base case

        if os.path.exists(headnotes_filepath) and not is_base_case:
            with open(headnotes_filepath, mode='r', encoding='utf-8') as head_file:
                raw_headnotes = head_file.read()
                #parser = ColieeHTMLParser()
                #parser.feed(raw_headnotes)
                #headnotes = parser.get_text()
                #parser.close()

                parser = ColieeSummaryHTMLParser()
                parser.feed(raw_headnotes)
                summary = parser.get_summary()
                parser.close()

                out_summary_file = os.path.join(output_folder, 'summary.txt')
                with open(out_summary_file, mode='w', encoding='utf-8') as summary_file:
                    summary_file.write(summary)

        return True
    else:
        return False


if __name__ == '__main__':
    prepare_ir_data('/Users/administrator/Documents/coliee2019/data_fetch/files',
                    '/Users/administrator/Documents/coliee2019/data_fetch/ir_task_new',
                    num_candidates_per_case=200)