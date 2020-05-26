import tkinter
from tkinter import *
from tkinter import messagebox
import os
from gui_commons import *
#from prepare_data import find_refs
from package_data import extract_paragraphs


INPUT_DIR = 'C:\\juliano\\dev\\data\\coliee2019\\data_prep\\IR_task2_refined_2'
RAW_CONTENT_DIR = 'C:\\juliano\\dev\\data\\coliee2019\\data_prep\\files_merged'

global dir_index, dir_list, entailing_index, entailing_list
NORMAL_PARAG_TAG = 'NPT'
ENTAILING_PARAG_TAG = 'EPT'
ENTAILING_EDIT_TAG = 'EET'
ENTAILED_FRAGMENT_TAG = 'EFT'
REFERENCE_TAG = 'REF'
REMOVED_REFERENCE_TAG = 'REM_REF'

PARAGRAPH_REF_PAT = re.compile('\\bpara(?:graph)?s?\\b')


def find_next_case (dir_index, dir_list):
    while dir_index < len(dir_list):
        case_id = dir_list[dir_index]
        entailed_sentence_filepath = os.path.join(INPUT_DIR, case_id, 'entailed_fragment.txt')
        skip_filepath = os.path.join(INPUT_DIR, case_id, 'skip.txt')
        if not os.path.exists(entailed_sentence_filepath) and not os.path.exists(skip_filepath):
            return dir_index
        else:
            dir_index += 1

    return -1


def load_next_case():
    global dir_index, dir_list

    next_index = find_next_case(dir_index, dir_list)
    if next_index < 0:
        messagebox.showinfo("Warning", "No more cases.")
    else:
        dir_index = next_index
        load_case(next_index, dir_list)


def find_paragraph_refs():
    occurs = re.finditer(PARAGRAPH_REF_PAT, text_entailed.get(1.0, END))
    parags = []
    for occur in occurs:
        parags.append((occur.start(), occur.end()))

    return parags


def highlight_parag_refs():
    ref_ranges = find_paragraph_refs()
    for ref in ref_ranges:
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


#def highlight_refs():
#    ref_ranges = find_refs(text_entailed.get(1.0, END))
#    for ref in ref_ranges:
#        text_entailed.tag_add(REFERENCE_TAG, index_to_text_coord(ref[0]), index_to_text_coord(ref[1]))


def load_case(case_index, dir_list):
    global entailing_list, entailing_index

    base_dir, case_filepath = get_current_base_dir_and_filepath()

    with open(case_filepath, mode='r', encoding='utf-8', errors='ignore') as f:
        contents = f.read()

    text_entailed.config(state=NORMAL)
    text_entailed .delete('1.0', END)
    text_entailed.insert(END, contents)
    text_entailed.config(state=DISABLED)

    var_lb_entailed.set(dir_list[case_index])

    entailing_index = 0
    load_entailing_case()
    highlight_parag_refs()


def load_entailing_case():
    global entailing_index, entailing_list

    base_dir, _ = get_current_base_dir_and_filepath()
    cited_dirpath = os.path.join(base_dir, 'cited')
    entailing_list = os.listdir(cited_dirpath)

    cited_case_filepath = get_current_entailing_filepath()

    with open(cited_case_filepath, mode='r', encoding='utf-8', errors='ignore') as f:
        contents = f.read()

    text_entailing.config(state=NORMAL)
    text_entailing .delete('1.0', END)
    text_entailing.insert(END, contents)
    text_entailing.config(state=DISABLED)

    var_lb_entailing.set(entailing_list[entailing_index])
    entailing_index = entailing_index


def load_next_entailing():
    global entailing_index

    next_ent_index = find_next_entailing()
    if next_ent_index < 0:
        messagebox.showinfo('Warning', 'No more entailing cases for this case.')
    else:
        entailing_index = next_ent_index
        load_entailing_case()


def find_next_entailing():
    global entailing_index, entailing_list

    if len(entailing_list) > entailing_index+1:
        return entailing_index+1
    else:
        return -1


def load_prev_entailing():
    global entailing_index

    prev_ent_index = find_prev_entailing()
    if prev_ent_index < 0:
        messagebox.showinfo('Warning', 'No more entailing cases for this case.')
    else:
        entailing_index= prev_ent_index
        load_entailing_case()

    return prev_ent_index


def find_prev_entailing():
    global entailing_index, entailing_list

    if entailing_index > 0:
        return entailing_index-1
    else:
        return -1


def key_pressed_entailed(event):
    if event.char == 'd':
        event.widget.tag_add(ENTAILED_FRAGMENT_TAG, event.widget.index(tkinter.SEL_FIRST), event.widget.index(tkinter.SEL_LAST))
        event.widget.tag_remove(SEL, 1.0, END)
    elif event.char == 'b':
        event.widget.tag_add(REMOVED_REFERENCE_TAG, event.widget.index(tkinter.SEL_FIRST),
                             event.widget.index(tkinter.SEL_LAST))
        event.widget.tag_remove(SEL, 1.0, END)


def save_case():
    if not save_entailed_fragment():
        messagebox.showwarning('Warning', 'Necessary to select exactly one entailed fragment')
        return False
    save_paragraphs()
    save_blackedout_entailed_case()

    return True


def save_blackedout_entailed_case():
    #global dir_index, dir_list

    REMOVED_REF_MARK = 'FRAGMENT_SUPPRESSED'

    case_dir, _ = get_current_base_dir_and_filepath()
    blackedout_filepath = os.path.join(case_dir, os.path.basename(case_dir)+'_blackedout.txt')

    contents = text_entailed.get(1.0, END)
    refs = text_entailed.tag_ranges(REMOVED_REFERENCE_TAG)

    index_ref = 0

    last_frag_end = 1.0
    blacked_out = ''

    while index_ref <= len(refs) - 2:
        blacked_out += text_entailed.get(last_frag_end, text_entailed.index(refs[index_ref])) + REMOVED_REF_MARK
        last_frag_end = text_entailed.index(refs[index_ref + 1])
        index_ref += 2

    blacked_out += text_entailed.get(last_frag_end, END)

    with open(blackedout_filepath, mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(blacked_out)


def save_paragraphs():
    entailing_filepath = get_current_entailing_filepath()
    case_dir, _ = get_current_base_dir_and_filepath()
    paragraphs_dir = os.path.join(case_dir, 'paragraphs', os.path.basename(entailing_filepath))
    os.makedirs(paragraphs_dir)

    normal_parag_ranges = text_entailing.tag_ranges(NORMAL_PARAG_TAG)
    entailing_parag_ranges = text_entailing.tag_ranges(ENTAILING_PARAG_TAG)

    contents = text_entailing.get(1.0, END)

    index_normal = 0
    index_entailing = 0

    parag_index = 1
    done = False
    while not done:
        if index_normal >= len(normal_parag_ranges):
            normal_start = None
        else:
            normal_start = get_num_coords(text_entailing.index(normal_parag_ranges[index_normal]))

        if index_entailing >= len(entailing_parag_ranges):
            entail_start = None
        else:
            entail_start = get_num_coords(text_entailing.index(entailing_parag_ranges[index_entailing]))

        done = normal_start is None and entail_start is None

        if not done:
            is_entail = False
            if entail_start is None or coords_before(normal_start, entail_start):
                parag_start = text_entailing.index(normal_parag_ranges[index_normal])
                parag_end = text_entailing.index(normal_parag_ranges[index_normal+1])
                index_normal += 2
            elif normal_start is None or coords_before(entail_start, normal_start):
                is_entail = True
                parag_start = text_entailing.index(entailing_parag_ranges[index_entailing])
                parag_end = text_entailing.index(entailing_parag_ranges[index_entailing + 1])
                index_entailing += 2

            parag_txt = text_entailing.get(parag_start, parag_end)
            parag_filepath = os.path.join(paragraphs_dir, ('%03d' % parag_index)+'_'+str(is_entail)+'.txt')
            with open(parag_filepath, mode='w', encoding='utf-8', errors='ignore') as f:
                f.write(parag_txt)

            parag_index += 1


def save_entailed_fragment():
    ent_frag_ranges = text_entailed.tag_ranges(ENTAILED_FRAGMENT_TAG)
    if len(ent_frag_ranges) != 2:
        return False

    frag_start = ent_frag_ranges[0]
    frag_end = ent_frag_ranges[1]

    case_dir, _ = get_current_base_dir_and_filepath()
    ent_frag_filepath = os.path.join(case_dir, 'entailed_fragment.txt')

    with open(ent_frag_filepath, mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(text_entailed.get(frag_start, frag_end))

    return True


def save_and_next():
    if save_case():
        load_next_case()


def skip():
    case_dir, _ = get_current_base_dir_and_filepath()
    skip_filepath = os.path.join(case_dir, 'skip.txt')
    with open(skip_filepath, mode='w', encoding='utf-8', errors='ignore') as f:
        f.write('.')

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


def get_current_base_dir_and_filepath():
    global dir_index, dir_list
    base_dir = os.path.join(INPUT_DIR, dir_list[dir_index])
    base_filepath = os.path.join(base_dir, dir_list[dir_index]+'.txt')

    return base_dir, base_filepath


def get_current_entailing_filepath():
    global entailing_index, entailing_list

    base_dir, _ = get_current_base_dir_and_filepath()
    cited_dirpath = os.path.join(base_dir, 'cited')

    return os.path.join(cited_dirpath, entailing_list[entailing_index])


def highlight_paragraphs():
    txt = text_entailing.get(1.0, END)
    parag_pat = re.compile('^ {0,3}\\[(\\d{1,3})\\]\\s+', re.MULTILINE)

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

    #if last_parag_start >= 0:
    #    text_entailing.tag_add(NORMAL_PARAG_TAG, '1.0+' + str(last_parag_start) + 'c',
     #                          '1.0+' + str(occur.start()) + 'c')


def find_last_parag_end(txt, cur_parag_start):
    occurs = re.finditer('[^\\s]', txt[cur_parag_start-20:cur_parag_start], re.MULTILINE)
    for last in occurs:
        pass

    return last.end() + len(txt[0:cur_parag_start-20])


if __name__ == '__main__':
    dir_index = 0
    dir_list = os.listdir(INPUT_DIR)
    entailing_index=0
    entailing_list=[]

    top = tkinter.Tk()
    top.title('COLIEE Case Law Entailment Data Prep')
    top.grid_rowconfigure(0, weight=1)
    #top.grid_rowconfigure(1, weight=1)
    top.grid_columnconfigure(0, weight=3)
    top.grid_columnconfigure(1, weight=3)
    top.grid_columnconfigure(2, weight=1)
    #top.attributes('-fullscreen', True)

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

    #text_entailed.bind('<Return>', enter_pressed)
    #text_entailed.bind('<Key>', key_pressed)

    #entailing (cited) frame:
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
    lb_entailing_case.grid(row=0, column=1, sticky=E + W)

    bt_prev_entailing = Button(fr_entailing, text='Previous', command=load_prev_entailing)
    bt_prev_entailing.grid(row=0, column=0)
    bt_next_entailing = Button(fr_entailing, text='Next', command=load_next_entailing)
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
    text_entailing.bind('<Alt-Up>', move_lower_bound_up)
    text_entailing.bind('<Alt-Down>', move_lower_bound_down)

    text_entailing.bind('<ButtonRelease-1>', bt1_release_entailing)

    # text_entailing.bind('<Return>', enter_pressed)
    #text_entailing.bind('<Key>', key_pressed)

    #FRAME INFO
    fr_info = Frame(top, bd=2, relief=SUNKEN)
    fr_info.grid_rowconfigure(0, weight=1)
    fr_info.grid_rowconfigure(1, weight=1)
    fr_info.grid_rowconfigure(2, weight=1)

    bt_save = Button(fr_info, text='Save', command=save_and_next)
    bt_save.grid(row=0, column=0)

    bt_skip = Button(fr_info, text='Skip', command=skip)
    bt_skip.grid(row=1, column=0)

    bt_parags = Button(fr_info, text='Paragraphs', command=highlight_paragraphs)
    bt_parags.grid(row=2, column=0)

    fr_info.grid(row=0, column=6)

    #Label(fr_info, text='Paragraph count: ')


    load_next_case()

    top.mainloop()

