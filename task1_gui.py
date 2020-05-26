import tkinter
from tkinter import *
from tkinter import messagebox
from tkinter.filedialog import askdirectory
from prepare_data import find_refs
import os
from package_data import extract_text
from gui_commons import *

CITATION_TAG = 'CITATION'
CANDIDATE_TAG = 'CANDIDATE'
REF_TAG = 'REFERENCE'

REMOVED_REF_TAG = 'REFERENCE_SUPPRESSED'
REMOVED_CIT_TAG = 'CITATION_SUPPRESSED'

CASE_REPOSITORY_PATH = 'C:\\juliano\\dev\\data\\coliee2019\\data_prep\\files_merged'

global refs
global ref_index
global ref_terms
global current_filepath
stoplist = ['and', 'the', 'many', 'under', 'over', 'very', 'for', 'with', 'see', 'the', 'that', 'this', 'other', 'also', 'there']
global dir_index
global dirlist
global dirpath


def reset_refs():
    global refs
    global ref_index

    refs = []
    ref_index = -1


def open_dir():
    global dir_index, dirlist, dirpath

    dirpath = askdirectory(initialdir = 'C:\\juliano\\dev\\data\\coliee2019\\data_prep\\IR_FILES_350\\')
    print('processing ', dirpath)
    dirlist = os.listdir(dirpath)
    dir_index = find_first_case()


def find_first_case():
    global dir_index, dirlist, dirpath

    dir_index = -1
    for folder in dirlist:
        case_dir = os.path.join(dirpath, folder)
        blackedout_file = os.path.join(case_dir, folder+'_blackedout.txt')
        if os.path.exists(blackedout_file):
            dir_index+= 1
        else:
            return dir_index

    return dir_index


def load_case(index):
    global dirlist, dirpath

    base_dir = os.path.join(CASE_REPOSITORY_PATH, dirlist[index])
    content_filepath = os.path.join(base_dir, 'contents.html')
    headnotes_filepath = os.path.join(base_dir, 'headnotes.html')

    contents = extract_text(content_filepath, headnotes_filepath)

    output_dir = os.path.join(dirpath, dirlist[index])
    output_filepath = os.path.join(output_dir, dirlist[index]+'_original.txt')
    with open(output_filepath, mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(contents)

    var_dir.set(dirlist[index])

    ref_mode = True
    return contents


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


def update_ref_terms(selected):
    global ref_terms

    occurs = re.finditer('\\b\\w+\\b', selected)
    for occur in occurs:
        term = selected[occur.start():occur.end()]
        if not re.match('\\d+', term) and len(term)>2 and term not in stoplist:
            ref_terms.add(term)


def next_case():
    global refs
    global dir_index, ref_mode

    reset_refs()
    lb_cits.delete(0, END)
    lb_refs.delete(0, END)
    dir_index += 1
    ref_mode = True
    ref_terms.clear()

    text.config(state=NORMAL)
    txt_contents = load_case(dir_index)
    text.delete('1.0', END)
    text.insert(END, txt_contents)
    refs = find_refs(txt_contents)
    highlight_candidates(refs)

    text.config(state=DISABLED)


def highlight_candidates(ranges):
    global refs
    new_refs = []

    existing_refs = text.tag_ranges(REF_TAG)
    for ref in ranges:
        if not range_in_refs(ref, existing_refs):
            text.tag_add(CANDIDATE_TAG, index_to_text_coord(ref[0]), index_to_text_coord(ref[1]))
            new_refs.append(ref)

    refs = new_refs


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
    global ref_index
    global refs
    global ref_mode

    last_ref_end = 0
    if ref_index >= 0:
        last_ref = refs[ref_index]
        text.tag_remove(CANDIDATE_TAG, index_to_text_coord(last_ref[0]), index_to_text_coord(last_ref[1]))
        last_ref_end = last_ref[1]

    next_range = text.tag_nextrange(CANDIDATE_TAG, index_to_text_coord(last_ref_end))
    if len(next_range) > 0:
        text.see(next_range[0])
        ref_index += 1
    elif ref_mode:
        print('no more refs')
        messagebox.showinfo("Warning", "No more references. Processing citations.")
        ref_mode = False
        text.tag_remove(CANDIDATE_TAG, 1.0, END)
        refs = find_citations()
        highlight_candidates(refs)
        ref_index = 0
        next_ref()
    else:
        messagebox.showinfo("Warning", "All done for this case.")
        save_file()


def save_file():
    global dirlist, dirpath, dir_index
    blacked_out = blackout_text()
    output_dir = os.path.join(dirpath, dirlist[dir_index])
    output_filepath = os.path.join(output_dir, dirlist[dir_index] + '_blackedout.txt')
    with open(output_filepath, mode='w', encoding='utf-8', errors='ignore') as f:
        f.write(blacked_out)


def find_citations():
    global ref_terms

    contents = text.get(1.0, END)
    pat = ''
    for term in ref_terms:
        if len(pat) > 0:
            pat += '|'
        pat += '(?:\\b'+term+'\\b)'

    occurs = re.finditer(pat, contents)
    res = []
    for occur in occurs:
        res.append((occur.start(), occur.end()))

    return res


def blackout_text():
    contents = text.get(1.0, END)
    refs = text.tag_ranges(REF_TAG)
    cits = text.tag_ranges(CITATION_TAG)

    index_ref = 0
    index_cit = 0

    last_frag_end = 1.0
    blacked_out = ''

    exit = False
    while not exit:
        if index_ref >= len(refs):
            ref_start = None
        else:
            ref_start = get_num_coords(text.index(refs[index_ref]))

        if index_cit >= len(cits):
            cit_start = None
        else:
            cit_start = get_num_coords(text.index(cits[index_cit]))

        exit = ref_start is None and cit_start is None

        if not exit:
            if cit_start is None or (ref_start is not None and coords_before(ref_start, cit_start)):
                blacked_out += text.get(last_frag_end, text.index(refs[index_ref])) + REMOVED_REF_TAG
                last_frag_end = text.index(refs[index_ref + 1])
                index_ref += 2
            elif ref_start is None or (cit_start is not None and coords_before(cit_start, ref_start)):
                blacked_out += text.get(last_frag_end, text.index(cits[index_cit])) + REMOVED_CIT_TAG
                last_frag_end = text.index(cits[index_cit + 1])
                index_cit += 2


    blacked_out += text.get(last_frag_end, END)

    return blacked_out


def key_pressed(event):
    print ("pressed", repr(event.char))
    if event.char == 'a':
        next_ref()


if __name__ == '__main__':
    ref_index = 0
    ref_terms = set()
    ref_mode = True
    dir_index = 0

    top = tkinter.Tk()
    top.title('COLIEE Case Law Data Prep')
    top.grid_rowconfigure(0, weight=1)
    top.grid_rowconfigure(1, weight=1)
    top.grid_columnconfigure(0, weight=1)
    #top.attributes('-fullscreen', True)

    menubar = Menu(top)
    filemenu = Menu(menubar, tearoff=0)
    filemenu.add_command(label="Open Dir", command=open_dir)
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

    bt_save = Button(fr_buttons, text='Save', command=save_file)
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

