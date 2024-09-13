import tkinter
from tkinter import *
from tkinter import messagebox
import os
import tkinter.messagebox
from gui_commons import *

import shutil
import re
import dbutils as db
import case_files_utils as cfu
import webbrowser
from langchain.text_splitter import TokenTextSplitter

from typing import List, Dict, Tuple
import openai

openai.organization = os.getenv('OPENAI_ORG')
openai.api_key = os.getenv('OPENAI_API_KEY')

OUTPUT_DIR = '/Users/jrabelo/Documents/coliee2025/task2_prep'

NORMAL_PARAG_TAG = 'NPT'
ENTAILING_PARAG_TAG = 'EPT'
ENTAILING_EDIT_TAG = 'EET'
ENTAILED_FRAGMENT_TAG = 'EFT'
REFERENCE_TAG = 'REF'
REMOVED_REFERENCE_TAG = 'REM_REF'

PARAGRAPH_REF_PAT = re.compile('\\bpara(?:graph)?s?\\b')
TITLE_PAT = None

noticed_iter = None
case_gen = db.task2_generator()


def load_next_case():
    try:
        case_id, noticed_ids = next(case_gen)
        load_case(case_id, noticed_ids)
    except StopIteration:
        messagebox.showinfo('Warning', 'No more cases.')


def find_paragraph_refs():
    return cfu.find_pattern_in_text(PARAGRAPH_REF_PAT, text_entailed.get(1.0, END))


def find_title_refs():
    return cfu.find_pattern_in_text(TITLE_PAT, text_entailed.get(1.0, END))


def highlight_parag_refs():
    parag_ranges = find_paragraph_refs()
    title_ranges = find_title_refs()
    for ref in parag_ranges+title_ranges:
        text_entailed.tag_add(REFERENCE_TAG, index_to_text_coord(ref[0]), index_to_text_coord(ref[1]))


def select_clicked_range():
    ranges = text_entailing.tag_ranges(NORMAL_PARAG_TAG)
    selected_range = select_range_containing(ranges, text_entailing.index(INSERT))
    if not selected_range:
        ranges = text_entailing.tag_ranges(ENTAILING_PARAG_TAG)
        selected_range = select_range_containing(ranges, text_entailing.index(INSERT))
        if not selected_range:
            messagebox.showinfo('Warning', 'No range at caret position')

    return selected_range


def select_range_containing(ranges, index):
    i=0
    while True:
        if i >= len(ranges):
            return None

        start = ranges[i]
        end = ranges[i+1]

        if text_entailing.compare(start, '<=', index) and text_entailing.compare(index, '<=', end):
            text_entailing.tag_add(ENTAILING_EDIT_TAG, start, end)
            return ranges[i:i+1]

        i += 2


def load_case(case_id, noticed_ids):
    global noticed_iter

    if len(noticed_ids) == 0:
        print('No cases cited by {}'.format(case_id))
        db.t2_save_case_db(case_id, None, None, None)
        load_next_case()
        return

    base_path = cfu.find_case_contents_path(case_id)
    if base_path is None:
        print('Skipping invalid case contents')
        db.t2_save_case_db(case_id, None, None, None)
        load_next_case()
        return

    print('Loading base case: {}'.format(case_id))
    contents = cfu.get_inner_text(base_path)

    text_entailed.config(state=NORMAL)
    text_entailed.delete('1.0', END)
    text_entailed.insert(END, contents)

    var_lb_entailed.set(case_id)

    noticed_iter = iter(noticed_ids)
    if load_entailing_case(False):
        highlight_parag_refs()
    else:
        load_next_case()


def is_cited_in_base_case(cited_id):
    global TITLE_PAT

    titles = db.get_titles(cited_id)
    base_contents = text_entailed.get(1.0, END)
    base_contents = re.sub(r'\s+', ' ', base_contents)

    if PARAGRAPH_REF_PAT.search(base_contents) is not None:
        title_pat_str = ''
        for title in titles:
            if len(title_pat_str) > 0:
                title_pat_str += '|'
            title = re.sub(r'\s+', ' ', title)
            title = title.replace('(', r'\(')
            title = title.replace(')', r'\)')
            title_pat_str += '(?:{})'.format(title)

        TITLE_PAT = re.compile(title_pat_str, flags=re.MULTILINE)

        if TITLE_PAT.search(base_contents) is not None:
            return True

    return False


def load_entailing_case(iterative_mode=True):
    global noticed_iter

    try:
        while True:
            cited_id = next(noticed_iter)
            if is_cited_in_base_case(cited_id):
                print('Loading cited case: {}'.format(cited_id))
                cited_path = cfu.find_case_contents_path(cited_id)

                if cited_path is None:
                    print('Skipping invalid case contents')
                    continue

                contents = cfu.get_inner_text(cited_path)

                text_entailing.config(state=NORMAL)
                text_entailing.delete('1.0', END)
                text_entailing.insert(END, contents)
                # text_entailing.config(state=DISABLED)  #works in Windows but makes Text not to respond to mouse/keyboard events in Macos

                var_lb_entailing.set(cited_id)

                highlight_paragraphs()

                return True
            else:
                text_entailing.config(state=NORMAL)
                text_entailing.delete('1.0', END)
                msg = 'Skipping case {} as it is not cited in the contents of the \
                    base case'.format(cited_id)
                text_entailing.insert(END, msg)
                var_lb_entailing.set(cited_id)

                if iterative_mode:
                    messagebox.showinfo('Warning', msg)
                else:
                    print(msg)

    except StopIteration:
        if iterative_mode:
            messagebox.showinfo('Warning', 'No more entailing cases for this case.')
        else:
            print('No more entailing cases for this case.')
            case_id = get_current_case_id()
            db.t2_save_case_db(case_id, None, None, None)

        return False


def load_prev_entailing():
    pass


def find_prev_entailing():
    pass


def key_pressed_entailed(event):
    if event.char == 'd':
        event.widget.tag_add(ENTAILED_FRAGMENT_TAG, event.widget.index(tkinter.SEL_FIRST),
                             event.widget.index(tkinter.SEL_LAST))
        event.widget.tag_remove(SEL, 1.0, END)
    elif event.char == 'b':
        event.widget.tag_add(REMOVED_REFERENCE_TAG, event.widget.index(tkinter.SEL_FIRST),
                             event.widget.index(tkinter.SEL_LAST))
        event.widget.tag_remove(SEL, 1.0, END)
    elif event.char == 'o':
        selected = event.widget.get(
            event.widget.index(tkinter.SEL_FIRST),
            event.widget.index(tkinter.SEL_LAST)
        )
        event.widget.tag_remove(SEL, 1.0, END)

        paragraphs = text_entailing.get(1.0, END)
    
        entailing_paragraphs = get_entailing_paragraphs(selected, paragraphs)
        if entailing_paragraphs:
            messagebox.showinfo('Entaling paragraphs', entailing_paragraphs)
        else:
            messagebox.showinfo('Info', 'No entailing paragraphs found')

    return 'break'


def get_entailing_paragraphs(fragment: str, paragraphs: str) -> List[str]:
    SAFETY_MARGIN = 200
    text_splitter = TokenTextSplitter(
        chunk_size=16 * 1024 - SAFETY_MARGIN, chunk_overlap=100
    )
    texts = text_splitter.split_text(paragraphs)

    results = []
    for text in texts:
        prompt = (
            'Consider the following legal case paragraphs:\n'
            '###\n'
            f'{text}\n'
            '###\n'
            'Considering the above paragraphs, output the paragraph numbers that entail the following conclusion:\n'
            '###\n'
            f'{fragment}\n'
            '###\n'
            'Output "none" if there is no paragraphs above that entail the given conclusion.'
        )

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=[
                    {"role": "system", "content": "You are an insightful legal expert."},
                    {"role": "user", "content": prompt},
                ]
            )
        except openai.error.InvalidRequestError as e:
            messagebox.showinfo('Error', e)
            return None

        result = response['choices'][0]['message']['content']

        if not 'none' == result.lower():
            results.append(result)

    return results


def save_case():
    case_id = get_current_case_id()
    noticed_id = get_current_noticed_id()
    output_case_dir = os.path.join(OUTPUT_DIR, cfu.filter_case_id(case_id))
    if os.path.exists(output_case_dir):
        shutil.rmtree(output_case_dir)

    os.makedirs(output_case_dir)

    entailed_frag = save_entailed_fragment(output_case_dir)
    if entailed_frag is None:
        messagebox.showwarning('Warning', 'Necessary to select exactly one entailed fragment')
        return False

    entailing_parags = save_paragraphs(output_case_dir)
    save_blackedout_entailed_case(output_case_dir)
    db.t2_save_case_db(case_id, noticed_id, entailed_frag, entailing_parags)

    return True


def save_blackedout_entailed_case(output_case_dir):
    REMOVED_REF_MARK = 'FRAGMENT_SUPPRESSED'

    refs = text_entailed.tag_ranges(REMOVED_REFERENCE_TAG)

    index_ref = 0

    last_frag_end = 1.0
    blacked_out = ''

    while index_ref <= len(refs) - 2:
        blacked_out += text_entailed.get(last_frag_end, text_entailed.index(refs[index_ref])) + REMOVED_REF_MARK
        last_frag_end = text_entailed.index(refs[index_ref + 1])
        index_ref += 2

    blacked_out += text_entailed.get(last_frag_end, END)

    blackedout_filepath = os.path.join(output_case_dir, 'base_case.txt')
    with open(blackedout_filepath, mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(blacked_out)


def get_current_case_id():
    return var_lb_entailed.get()


def get_current_noticed_id():
    return var_lb_entailing.get()


def save_paragraphs(output_case_dir):
    entailing_parags = []
    paragraphs_dir = os.path.join(output_case_dir, 'paragraphs')
    os.makedirs(paragraphs_dir)

    normal_parag_ranges = text_entailing.tag_ranges(NORMAL_PARAG_TAG)
    entailing_parag_ranges = text_entailing.tag_ranges(ENTAILING_PARAG_TAG)

    index_normal = 0
    index_entailing = 0

    parag_index = 1
    done = False
    while not done:
        if index_normal >= len(normal_parag_ranges):
            normal_start = None
        else:
            normal_start = normal_parag_ranges[index_normal]

        if index_entailing >= len(entailing_parag_ranges):
            entail_start = None
        else:
            entail_start = get_num_coords(text_entailing.index(entailing_parag_ranges[index_entailing]))
            entail_start = entailing_parag_ranges[index_entailing]

        done = normal_start is None and entail_start is None

        if not done:
            is_entail = False
            if entail_start is None or (normal_start is not None and text_entailing.compare(normal_start, '<=', entail_start)): # coords_before(normal_start, entail_start)):
                parag_start = normal_parag_ranges[index_normal]
                parag_end = normal_parag_ranges[index_normal+1]
                index_normal += 2
            elif normal_start is None or (entail_start is not None and text_entailing.compare(entail_start, '<=', normal_start)): # coords_before(entail_start, normal_start)):
                is_entail = True
                parag_start = entailing_parag_ranges[index_entailing]
                parag_end = entailing_parag_ranges[index_entailing + 1]
                index_entailing += 2

            parag_txt = text_entailing.get(parag_start, parag_end)
            parag_filepath = os.path.join(paragraphs_dir, ('%03d' % parag_index)+'.txt')
            with open(parag_filepath, mode='w', encoding='utf-8', errors='ignore') as f:
                f.write(parag_txt)

            if is_entail:
                entailing_parags.append(parag_index)

            parag_index += 1

    return entailing_parags


def save_entailed_fragment(output_case_dir):
    ent_frag_ranges = text_entailed.tag_ranges(ENTAILED_FRAGMENT_TAG)
    if len(ent_frag_ranges) != 2:
        return None

    frag_start = ent_frag_ranges[0]
    frag_end = ent_frag_ranges[1]

    ent_frag_filepath = os.path.join(output_case_dir, 'entailed_fragment.txt')
    with open(ent_frag_filepath, mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(text_entailed.get(frag_start, frag_end))

    return text_entailed.get(frag_start, frag_end)


def save_and_next():
    if save_case():
        load_next_case()


def skip():
    case_id = get_current_case_id()
    db.t2_save_case_db(case_id, None, None, None)

    load_next_case()


def bt1_release_entailing(event):
    sel_range = event.widget.tag_ranges(SEL)
    if sel_range:
        event.widget.tag_add(NORMAL_PARAG_TAG, event.widget.index(tkinter.SEL_FIRST),
                             event.widget.index(tkinter.SEL_LAST))
        event.widget.tag_remove(SEL, 1.0, END)
    else:
        select_clicked_range()


def key_pressed_entailing(event):
    print('key pressed: '+event.char + ' - code: '+str(event.keycode))
    if event.keycode == 8:
        edit_parag_range = text_entailing.tag_ranges(ENTAILING_EDIT_TAG)
        if edit_parag_range:
            text_entailing.tag_remove(ENTAILING_EDIT_TAG, edit_parag_range[0], edit_parag_range[1])
            text_entailing.tag_remove(NORMAL_PARAG_TAG, edit_parag_range[0], edit_parag_range[1])
            text_entailing.tag_remove(ENTAILING_PARAG_TAG, edit_parag_range[0], edit_parag_range[1])
        else:
            delete_last_entailing_parag()
    elif event.char == 'e':
        edit_parag_range = text_entailing.tag_ranges(ENTAILING_EDIT_TAG)
        if edit_parag_range:
            text_entailing.tag_remove(ENTAILING_EDIT_TAG, edit_parag_range[0], edit_parag_range[1])
            text_entailing.tag_remove(NORMAL_PARAG_TAG, edit_parag_range[0], edit_parag_range[1])
            text_entailing.tag_add(ENTAILING_PARAG_TAG, edit_parag_range[0], edit_parag_range[1])
        else:
            mark_last_entailing_parag()
            sel_range = event.widget.tag_ranges(SEL)
            if sel_range:
                event.widget.tag_add(ENTAILING_PARAG_TAG, SEL_FIRST, SEL_LAST)
                event.widget.tag_remove(SEL, 1.0, END)
    elif event.keycode == 13:
        save_edit_parag()

    print('done')

    return 'break'


def save_edit_parag():
    range = text_entailing.tag_ranges(ENTAILING_EDIT_TAG)
    if range:
        text_entailing.tag_remove(ENTAILING_EDIT_TAG, 1.0, END)


def move_lower_bound_up(event):
    move_bounds(False, False, True, False)


def move_lower_bound_down(event):
    move_bounds(False, False, False, True)


def move_upper_bound_up(event):
    move_bounds(True, False, False, False)


def move_upper_bound_down(event):
    move_bounds(False, True, False, False)


def move_bounds(upper_up, upper_down, lower_up, lower_down):
    sel_range = text_entailing.tag_ranges(ENTAILING_EDIT_TAG)
    if sel_range:
        old_start = sel_range[0]
        old_end = sel_range[1]
        new_start = old_start
        new_end = old_end
        if upper_up:
            new_start = str(sel_range[0]) + '-1 line linestart'
        elif upper_down:
            new_start = str(sel_range[0]) + '+1 line linestart'
        elif lower_up:
            new_end = str(sel_range[1]) + '-1 line lineend'
        elif lower_down:
            new_end = str(sel_range[1]) + '+1 line lineend'

        text_entailing.tag_remove(NORMAL_PARAG_TAG, old_start, old_end)
        text_entailing.tag_add(NORMAL_PARAG_TAG, new_start, new_end)
        text_entailing.tag_remove(ENTAILING_EDIT_TAG, old_start, old_end)
        text_entailing.tag_add(ENTAILING_EDIT_TAG, new_start, new_end)


def delete_last_entailing_parag():
    ranges = text_entailing.tag_ranges(NORMAL_PARAG_TAG)
    if ranges:
        last_range_start = ranges[-2]
        last_range_end = ranges[-1]

        text_entailing.tag_remove(NORMAL_PARAG_TAG, last_range_start, last_range_end)

        return last_range_start, last_range_end
    else:
        return None, None


def mark_last_entailing_parag():
    last_range_start, last_range_end = delete_last_entailing_parag()
    if last_range_start:
        text_entailing.tag_add(ENTAILING_PARAG_TAG, last_range_start, last_range_end)


def highlight_paragraphs():
    txt = text_entailing.get(1.0, END)
    parag_pat = re.compile(r'^ {0,3}\[(\d{1,3})\]\s+', re.MULTILINE)

    occurs = re.finditer(parag_pat, txt)
    last_parag_num = 0
    last_parag_start = -1
    for occur in occurs:
        parag_num = int(occur.group(1))
        if parag_num == last_parag_num+1:
            print('found paragrapth #' + str(parag_num))
            if last_parag_start >= 0:
                last_parag_end = find_last_parag_end(txt, occur.start())
                text_entailing.tag_add(NORMAL_PARAG_TAG, '1.0+'+str(last_parag_start)+'c', '1.0+'+str(last_parag_end) +'c')

            last_parag_start = occur.start()
            last_parag_num += 1


def find_last_parag_end(txt, cur_parag_start):
    occurs = re.finditer('[^\\s]', txt[cur_parag_start-20:cur_parag_start], re.MULTILINE)
    for last in occurs:
        pass

    return last.end() + len(txt[0:cur_parag_start-20])


def help():
    tkinter.messagebox.showinfo(
        title="Help",
        message="Help",
        detail=(
            "- Entailed case (left box):\n"
            "|-- First, select a fragment of text. These are the commands available: \n"
            "|---- d: highlights the decision (GREEN). Only one fragment can be marked as 'decision';\n"
            "|---- b: 'blocks' content: the fragment is removed from the content file because it may contain information that give away the answer (ORANGE). Any number of fragments can be marked as 'blocked';\n\n"
            "- Entaling case (right box):\n"
            "|-- clicking a paragraph will select it (RED).\n"
            "|-- you can change the bounds of a selected paragraph if the auto paragraph detection didn't work:\n"
            "|---- UP/DOWN: moves the upper bounds;\n"
            "|---- LEFT/RIGHT: moves the lower bounds.\n"
            "|-- e: marks the selected paragraph as 'entailing' (BROWN). You can mark one or more paragraphs as 'entailing'."
        )
    )

def open_case(event):
    case_id = cfu.filter_case_id(event.widget.cget('text'))
    print('Opening case {}'.format(case_id))
    html_filepath = cfu.find_case_contents_path(case_id)
    webbrowser.get('safari').open_new('file://'+html_filepath)


if __name__ == '__main__':
    top = tkinter.Tk()
    top.title('COLIEE Case Law Entailment Data Prep')
    top.grid_rowconfigure(0, weight=1)
    top.grid_columnconfigure(0, weight=3)
    top.grid_columnconfigure(1, weight=3)
    top.grid_columnconfigure(2, weight=1)

    fr_entailed = Frame(top, bd=2, relief=SUNKEN)

    fr_entailed.grid_rowconfigure(0, weight=1)
    fr_entailed.grid_rowconfigure(1, weight=100)
    fr_entailed.grid_columnconfigure(0, weight=1)

    yscrollbar_entailed = Scrollbar(fr_entailed)
    yscrollbar_entailed.grid(row=1, column=1, sticky=N + S)

    var_lb_entailed = StringVar()
    var_lb_entailed.set('Entailed case')
    lb_entailed_case = Label(fr_entailed, textvariable=var_lb_entailed)
    lb_entailed_case.grid(row=0, column=0)
    lb_entailed_case.bind('<Button-1>', open_case)

    text_entailed = Text(fr_entailed, wrap=WORD, yscrollcommand=yscrollbar_entailed.set)
    text_entailed.grid_rowconfigure(0, weight=1)
    text_entailed.grid_columnconfigure(0, weight=1)
    text_entailed.grid(row=1, column=0, sticky=N + S + E + W)

    yscrollbar_entailed.config(command=text_entailed.yview)
    fr_entailed.grid(row=0, column=0, columnspan=1, rowspan=1, sticky=N + S + E + W)

    text_entailed.tag_config(ENTAILED_FRAGMENT_TAG, background="green", foreground="white")
    text_entailed.tag_config(REFERENCE_TAG, background="red", foreground="white")
    text_entailed.tag_config(REMOVED_REFERENCE_TAG, background="orange", foreground="blue")
    text_entailed.tag_raise(SEL)
    text_entailed.bind('<Key>', key_pressed_entailed)

    # entailing (cited) frame:
    fr_entailing = Frame(top, bd=2, relief=SUNKEN)

    fr_entailing.grid_rowconfigure(0, weight=1)
    fr_entailing.grid_rowconfigure(1, weight=100)
    fr_entailing.grid_columnconfigure(0, weight=1)
    fr_entailing.grid_columnconfigure(1, weight=1)
    fr_entailing.grid_columnconfigure(2, weight=1)

    yscrollbar_entailing = Scrollbar(fr_entailing)
    yscrollbar_entailing.grid(row=1, column=4, sticky=N + S)

    var_lb_entailing = StringVar()
    var_lb_entailing.set('Entailing case')
    lb_entailing_case = Label(fr_entailing, textvariable=var_lb_entailing)
    lb_entailing_case.bind('<Button-1>', open_case)
    lb_entailing_case.grid(row=0, column=1, sticky=E + W)

    bt_next_entailing = Button(fr_entailing, text='Next', command=load_entailing_case)
    bt_next_entailing.grid(row=0, column=2)

    text_entailing = Text(fr_entailing, wrap=WORD, yscrollcommand=yscrollbar_entailing.set)
    text_entailing.grid_rowconfigure(0, weight=1)
    text_entailing.grid_columnconfigure(0, weight=1)
    text_entailing.grid(row=1, column=0, columnspan=3, sticky=N + S + E + W)

    yscrollbar_entailing.config(command=text_entailing.yview)
    fr_entailing.grid(row=0, column=1, columnspan=1, rowspan=1, sticky=N + S + E + W)

    text_entailing.tag_config(NORMAL_PARAG_TAG, background="yellow", foreground="blue")
    text_entailing.tag_config(ENTAILING_PARAG_TAG, background="brown", foreground="yellow")
    text_entailing.tag_config(ENTAILING_EDIT_TAG, background="red", foreground="white")
    text_entailing.tag_raise(SEL)

    text_entailing.bind('<Key>', key_pressed_entailing)

    text_entailing.bind('<Up>', move_upper_bound_up)
    text_entailing.bind('<Down>', move_upper_bound_down)
    text_entailing.bind('<Left>', move_lower_bound_up)
    text_entailing.bind('<Right>', move_lower_bound_down)

    text_entailing.bind('<ButtonRelease-1>', bt1_release_entailing)

    # FRAME INFO
    fr_info = Frame(top, bd=2, relief=SUNKEN)
    fr_info.grid_rowconfigure(0, weight=1)
    fr_info.grid_rowconfigure(1, weight=1)
    fr_info.grid_rowconfigure(2, weight=1)

    bt_save = Button(fr_info, text='Save', command=save_and_next)
    bt_save.grid(row=0, column=0)

    bt_parags = Button(fr_info, text="Help", command=help)
    bt_parags.grid(row=1, column=0)

    bt_skip = Button(fr_info, text='Skip', command=skip)
    bt_skip.grid(row=2, column=0)

    # bt_parags = Button(fr_info, text='Paragraphs', command=highlight_paragraphs)
    # bt_parags.grid(row=2, column=0)

    fr_info.grid(row=0, column=6)

    load_next_case()

    top.mainloop()
