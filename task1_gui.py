import tkinter
from tkinter import *
from tkinter import messagebox
from tkinter.filedialog import askdirectory
from prepare_data import find_refs
import os
from package_data import extract_text
from gui_commons import *
import dbutils as db
import case_files_utils as cfu

CITATION_TAG = 'CITATION'
CANDIDATE_TAG = 'CANDIDATE'
REF_TAG = 'REFERENCE'

REMOVED_REF_TAG = 'REFERENCE_SUPPRESSED'
REMOVED_CIT_TAG = 'CITATION_SUPPRESSED'

CASE_REPOSITORY_PATH = '/Users/jrabelo/Documents/coliee2020/Compass Federal Court Cases for COLIEE - 2020/HTML files'
OUTPUT_PATH = '/Users/jrabelo/Documents/coliee2020/task1_prep'

global ref_terms
global current_filepath
global current_case_id
global last_range
stoplist = ['and', 'the', 'many', 'under', 'over', 'very', 'for', 'with', 'see', 'the', 'that', 'this', 'other', 'also', 'there']


case_gen = db.task1_generator()


def reset_refs():
    global last_range
    last_range = None


def key_pressed(event):
    pass
    #print('pressed', repr(event.char))


def enter_pressed(event):
    print('enter pressed on: '+event.widget.winfo_name())

    selected = text.selection_get()
    print(selected)

    if ref_mode:
        update_ref_terms(selected)
        lb_refs.insert(END, selected)
        event.widget.tag_add(REF_TAG, event.widget.index(tkinter.SEL_FIRST), event.widget.index(tkinter.SEL_LAST))
    else:
        lb_cits.insert(END, selected)
        event.widget.tag_add(CITATION_TAG, event.widget.index(tkinter.SEL_FIRST), event.widget.index(tkinter.SEL_LAST))

    event.widget.tag_remove(CANDIDATE_TAG, event.widget.index(tkinter.SEL_FIRST), event.widget.index(tkinter.SEL_LAST))
    text.tag_remove(SEL, 1.0, END)

    next_ref()

    return 'break'


def update_ref_terms(selected):
    global ref_terms

    occurs = re.finditer('\\b\\w+\\b', selected)
    for occur in occurs:
        term = selected[occur.start():occur.end()]
        if not re.match('\\d+', term) and len(term)>2 and term not in stoplist:
            ref_terms.add(term)


def next_case():
    global ref_mode
    global current_case_id

    reset_refs()
    lb_cits.delete(0, END)
    lb_refs.delete(0, END)

    ref_mode = True
    ref_terms.clear()

    txt_contents = ''
    try:
        found = False
        while not found:
            case_id = next(case_gen)
            print('Processing case {}'.format(case_id))
            if db.has_valid_citations(case_id, 5):
                html_filepath = cfu.find_case_contents_path(case_id)
                txt_contents = cfu.get_inner_text(html_filepath)
                current_case_id = case_id
                found = True
            else:
                print('Skipping case {} as it doesn\'t have enough valid citations'.format(case_id))

    except StopIteration:
        messagebox.showinfo("Warning", "No more cases.")

    text.config(state=NORMAL)
    text.delete('1.0', END)
    text.insert(END, txt_contents)
    ranges = find_refs(txt_contents)
    highlight_candidates(ranges)
    # text.config(state=DISABLED)


def highlight_candidates(ranges):
    existing_refs = text.tag_ranges(REF_TAG)
    for ref in ranges:
        if not range_in_refs(ref, existing_refs):
            text.tag_add(CANDIDATE_TAG, index_to_text_coord(ref[0]), index_to_text_coord(ref[1]))


def range_in_refs(a_range, existing_refs):
    range_start_str = text.index(index_to_text_coord(a_range[0]))
    range_end_str = text.index(index_to_text_coord(a_range[1]))
    range_start = get_num_coords(range_start_str)
    range_end = get_num_coords(range_end_str)
    for i in range(0, len(existing_refs), 2):
        ref_start = get_num_coords(text.index(existing_refs[i]))
        ref_end = get_num_coords(text.index(existing_refs[i+1]))
        if range_contains((ref_start, ref_end), (range_start, range_end)):
            return True

    return False


def prev_case():
    pass


def prev_ref():
    pass


def next_ref():
    global ref_mode
    global last_range

    if last_range is not None:
        text.tag_remove(CANDIDATE_TAG, last_range[0], last_range[1])
        text.tag_remove(SEL, last_range[0], last_range[1])
        next_range = text.tag_nextrange(CANDIDATE_TAG, last_range[1])
    else:
        next_range = text.tag_nextrange(CANDIDATE_TAG, 1.0)

    if len(next_range) > 0:
        text.see(next_range[1]+'+10l')
        text.tag_add(SEL, next_range[0], next_range[1])
        last_range = next_range
    elif ref_mode:
        print('no more refs')
        messagebox.showinfo("Warning", "No more references. Processing citations.")
        ref_mode = False
        text.tag_remove(CANDIDATE_TAG, 1.0, END)
        ranges = find_citations()
        highlight_candidates(ranges)
        reset_refs()
        next_ref()
    else:
        messagebox.showinfo("Warning", "All done for this case.")
        save_case()


def save_case():
    blacked_out = blackout_text()
    if not os.path.exists(OUTPUT_PATH):
        os.makedirs(OUTPUT_PATH)

    output_filepath = os.path.join(OUTPUT_PATH, '{}.txt'.format(cfu.filter_case_id(current_case_id)))
    with open(output_filepath, mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(blacked_out)

    save_case_db()


def save_case_db():
    db.t1_save_case_db(current_case_id)


def find_citations():
    global ref_terms

    contents = text.get(1.0, END)
    pat = ''
    for term in ref_terms:
        if len(pat) > 0:
            pat += '|'
        pat += '(?:\\b'+term+'\\b)'

    occurs = cfu.find_pattern_in_text(pat, contents)
    return occurs


def blackout_text():
    refs = text.tag_ranges(REF_TAG)
    cits = text.tag_ranges(CITATION_TAG)

    index_ref = 0
    index_cit = 0

    last_frag_end = 1.0
    blacked_out = ''

    done = False
    while not done:
        if index_ref >= len(refs):
            ref_start = None
        else:
            ref_start = refs[index_ref]

        if index_cit >= len(cits):
            cit_start = None
        else:
            cit_start = cits[index_cit]

        done = ref_start is None and cit_start is None

        if not done:
            if cit_start is None or (ref_start is not None and text.compare(ref_start, '<=', cit_start)):
                blacked_out += text.get(last_frag_end, text.index(refs[index_ref])) + REMOVED_REF_TAG
                last_frag_end = text.index(refs[index_ref + 1])
                index_ref += 2
            elif ref_start is None or (cit_start is not None and text.compare(cit_start, '<=', ref_start)):
                blacked_out += text.get(last_frag_end, text.index(cits[index_cit])) + REMOVED_CIT_TAG
                last_frag_end = text.index(cits[index_cit + 1])
                index_cit += 2

    blacked_out += text.get(last_frag_end, END)

    return blacked_out


def key_pressed(event):
    #print("pressed", repr(event.char))
    if event.char == 'a':
        next_ref()
    elif event.char == ' ':
        selected = text.selection_get()
        print(selected)
        clear_tags_for_string(selected)
        next_ref()
    elif event.char == '\uf702':    #left arrow
        move_bounds(False, False)
    elif event.char == '\uf703':    #right arrow
        move_bounds(False, True)
    elif event.char == '\uf700':    #up arrow
        move_bounds(True, False)
    elif event.char == '\uf701':    #down arrow
        move_bounds(True, True)

    return 'break'


def move_bounds(right_bound, right_direction):
    sel_range = text.tag_ranges(SEL)
    if sel_range:
        selected_text = text.get(sel_range[0], sel_range[1])
        only_one_word_selected = selected_text.count(' ') == 0
        old_start = sel_range[0]
        old_end = sel_range[1]
        new_start = old_start
        new_end = old_end

        if right_bound and right_direction:
            new_end = str(old_end) + '+1c wordend'
        elif right_bound and not right_direction:
            new_end = str(old_end) + '-1c wordstart'
        elif not right_bound and right_direction:
            new_start = str(old_start) + '+1c wordend'
        else:
            new_start = str(old_start) + '-1c wordstart'

        if text.compare(new_start, '>=', new_end):  #keep at least one word selected
            return

        text.tag_remove(CANDIDATE_TAG, old_start, old_end)
        text.tag_add(CANDIDATE_TAG, new_start, new_end)
        text.tag_remove(SEL, old_start, old_end)
        text.tag_add(SEL, new_start, new_end)


def clear_tags_for_string(s):
    occurs = cfu.find_pattern_in_text(s, text.get(1.0, END))
    for occur in occurs:
        text.tag_remove(CANDIDATE_TAG, index_to_text_coord(occur[0]), index_to_text_coord(occur[1]))


if __name__ == '__main__':
    ref_index = 0
    ref_terms = set()
    ref_mode = True
    dir_index = 0
    last_range = None

    top = tkinter.Tk()
    top.title('COLIEE Case Law Data Prep')
    top.grid_rowconfigure(0, weight=1)
    top.grid_rowconfigure(1, weight=1)
    top.grid_columnconfigure(0, weight=1)
    #top.attributes('-fullscreen', True)

    menubar = Menu(top)
    filemenu = Menu(menubar, tearoff=0)
    #filemenu.add_command(label="Open Dir", command=open_dir)
    filemenu.add_separator()
    filemenu.add_command(label="Exit", command=top.quit)
    menubar.add_cascade(label="File", menu=filemenu)
    top.config(menu=menubar)

    frame = Frame(top, bd=2, relief=SUNKEN)

    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    yscrollbar = Scrollbar(frame)
    yscrollbar.grid(row=0, column=1, sticky=N + S)

    text = Text(frame, wrap=WORD, yscrollcommand=yscrollbar.set)
    text.grid_rowconfigure(0, weight=1)
    text.grid_columnconfigure(0, weight=1)
    text.grid(row=0, column=0, sticky=N + S + E + W)

    yscrollbar.config(command=text.yview)
    frame.grid(row=0, column=0, columnspan=5, rowspan=2, sticky=N + S + E + W)

    text.bind('<Return>', enter_pressed)
    text.bind('<Key>', key_pressed)

    #fr_refs = Frame(top, bd=2, relief=SUNKEN)

    lb_refs = Listbox(top)
    lb_refs.grid_rowconfigure(0, weight=1)
    lb_refs.grid(row=0, column=5, columnspan=3, sticky=S+N)

    lb_cits = Listbox(top)
    lb_cits.grid_rowconfigure(1, weight=1)
    lb_cits.grid(row=1, column=5, columnspan=3, sticky=S+N)

    fr_buttons = Frame(top, bd=2, relief=SUNKEN)

    fr_buttons.grid_rowconfigure(0, weight=1)
    fr_buttons.grid_columnconfigure(0, weight=1)

    bt_prev_ref = Button(fr_buttons, text="Previous ref", command=prev_ref)
    bt_prev_ref.grid(row=0, column=3, sticky=W)
    bt_next_ref = Button(fr_buttons, text="Next ref", command=next_ref)
    bt_next_ref.grid(row=0, column=4, sticky=W)
    #bt_next_ref.bind('<Tab>', next_ref)

    bt_save = Button(fr_buttons, text='Save', command=save_case)
    bt_save.grid(row=0, column=5, sticky=E)

    bt_next_case = Button(fr_buttons, text="Previous case", command=prev_case)
    bt_next_case.grid(row=0, column=0, sticky=E)
    bt_prev_case = Button(fr_buttons, text="Next case", command=next_case)
    bt_prev_case.grid(row=0, column=1, sticky=E)

    var_dir = StringVar()
    lb_dir = Label(fr_buttons, textvariable=var_dir)
    lb_dir.grid(row=1, column=2)

    fr_buttons.grid(row=3, column=0, columnspan=5, rowspan=2, sticky=E + W)

    text.tag_config(CITATION_TAG, background="yellow", foreground="blue")
    text.tag_config(REF_TAG, background="brown", foreground="yellow")
    text.tag_config(CANDIDATE_TAG, background="red", foreground="white")
    text.tag_raise(SEL)

    citation_list = Frame(master=top, height=100, bd=2, relief=SUNKEN)
    citation_list.grid(row=0, column=5, columnspan=3)

    top.mainloop()

