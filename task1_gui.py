import tkinter
from tkinter import *
from tkinter.filedialog import askdirectory
from prepare_data import find_refs

CITATION_TAG = 'CITATION'
CANDIDATE_TAG = 'CANDIDATE'

global refs
global ref_index


def reset_refs():
    global refs
    global ref_index

    refs = []
    ref_index = -1

def open_dir():
    dirpath = askdirectory(initialdir = 'C:\\juliano\\dev\\data\\coliee2019\\data_prep\\files_merged\\')
    print(dirpath)


def load_case(case_dir):
    path = 'C:\\juliano\\dev\\data\\coliee2019\\data_prep\\IR_FILES_350\\r06p2yed4fporky\\fact.txt'
    with open(path, mode='r', encoding='utf-8', errors='ignore') as fin:
        txt = fin.read()
        return txt

def key_pressed(event):
    pass
    #print('pressed', repr(event.char))

def enter_pressed(event):
    print('enter pressed on: '+event.widget.winfo_name())
    event.widget.tag_remove(CANDIDATE_TAG, event.widget.index(tkinter.SEL_FIRST), event.widget.index(tkinter.SEL_LAST))
    event.widget.tag_add(CITATION_TAG, event.widget.index(tkinter.SEL_FIRST), event.widget.index(tkinter.SEL_LAST))
    text.tag_remove(SEL, 1.0, END)


def next_case():
    global refs

    reset_refs()

    text.config(state=NORMAL)
    txt_contents = load_case('')
    text.delete('1.0', END)
    text.insert(END, txt_contents)
    refs = find_refs(txt_contents)
    for ref in refs:
        text.tag_add(CANDIDATE_TAG, index_to_text_coord(ref[0]), index_to_text_coord(ref[1]))

    text.config(state=DISABLED)


def index_to_text_coord(index):
    return '1.0+'+str(index)+'c'


def prev_case():
    pass


def prev_ref():
    pass


def next_ref():
    global ref_index
    global refs

    last_ref_end = 0
    if ref_index >= 0:
        last_ref = refs[ref_index]
        text.tag_remove(CANDIDATE_TAG, index_to_text_coord(last_ref[0]), index_to_text_coord(last_ref[1]))
        last_ref_end = last_ref[1]

    next_range = text.tag_nextrange(CANDIDATE_TAG, index_to_text_coord(last_ref_end))
    if len(next_range) > 0:
        text.see(next_range[0])
        ref_index += 1
    else:
        print('no more refs')


if __name__ == '__main__':
    ref_index = 0

    top = tkinter.Tk()
    #top.attributes('-fullscreen', True)

    menubar = Menu(top)
    filemenu = Menu(menubar, tearoff=0)
    filemenu.add_command(label="Open Dir", command=open_dir)
    filemenu.add_separator()
    filemenu.add_command(label="Exit", command=top.quit)
    menubar.add_cascade(label="File", menu=filemenu)
    top.config(menu=menubar)

    text = Text(top)

    text.grid(row=0, column=0, columnspan=5)
    #text.config(state=DISABLED)
    #text.bind('<Key>', key_pressed)
    text.bind('<Return>', enter_pressed)

    bt_next_ref = Button(top, text="Previous ref", command=prev_ref)
    bt_next_ref.grid(row=1, column=0)
    bt_prev_ref = Button(top, text="Next ref", command=next_ref)
    bt_prev_ref.grid(row=1, column=1)

    bt_next_case = Button(top, text="Previous case", command=prev_case)
    bt_next_case.grid(row=2, column=0)
    bt_prev_case = Button(top, text="Next case", command=next_case)
    bt_prev_case.grid(row=2, column=1)

    text.tag_config(CITATION_TAG, background="yellow", foreground="blue")
    text.tag_config(CANDIDATE_TAG, background="red", foreground="white")
    text.tag_raise(SEL)

    citation_list = Frame(master=top, height=100, bd=2, relief=SUNKEN)
    citation_list.grid(row=0, column=5, columnspan=3)

    top.mainloop()

