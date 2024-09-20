import case_files_utils as cfu
import os
import sqlite3

T1_SELECT_CASES = 'select distinct c.id from citations cit, cases c \
    left join prepared_t1 p1 on c.id = p1.base_id \
    left join prepared_t2 p2 on c.id = p2.base_id \
    where \
    c.id = cit.caseid and \
    p1.base_id is null and \
    p2.base_id is null and \
    c.uri_VLEX is not null and \
    c.URI_vlex <> cit.cited_URI_vlex limit 5000, 10000'

T2_SELECT_CASES_ORDER_BY_CITATION_COUNT = 'select c.id, count(cit.id) as cit_count from citations cit, cases c \
    left join prepared_t1 p1 on c.id = p1.base_id \
    left join prepared_t2 p2 on c.id = p2.base_id \
    where c.id = cit.caseid and \
    p1.base_id is null and p2.base_id is null and c.uri_VLEX is not null and \
    c.uri_VLEX <> cit.cited_uri_VLEX \
    group by c.id having cit_count > 1 order by cit_count ASC'

SELECT_CASES = 'select c.id from cases c left join prepared_t2 p \
        on c.id = p.base_id where p.base_id is null and c.uri_VLEX is not null'

SELECT_CITATIONS_FOR_CASE = 'SELECT c.id FROM citations cit, cases c \
            where cit.caseid = \'{}\' and cit.cited_URI_vlex = c.URI_vlex and cit.cited_URI_vlex is not null \
            and cit.caseid <> c.id'

T2_SELECT_TITLES_FOR_CASE = 'SELECT title FROM titles where caseid = \'{}\''

# exporting

T1_SELECT_PREPARED_CASES = 'select base_id from prepared_t1 where export_id is NULL'

T2_SELECT_PREPARED_CASES = 'SELECT * FROM prepared_t2 where noticed_id is not null and prep_ts is not null and prep_ts >= "2023-10-01 21:52:26"'

CONN = None

def get_connection():
    global CONN
    if CONN is None:
        CONN = sqlite3.connect("coliee.db")
    return CONN


def task2_generator():
    cnx = get_connection()

    cursor = cnx.cursor()
    cursor.execute(T2_SELECT_CASES_ORDER_BY_CITATION_COUNT)

    for case_id in cursor:
        case_id = case_id[0]
        yield case_id, get_cited_by(case_id, cnx)

    cursor.close()


def get_cited_by(case_id, cnx):
    new_cnx = False
    if cnx is None:
        cnx = get_connection()
        new_cnx = True

    cursor_cited = cnx.cursor()
    cursor_cited.execute(SELECT_CITATIONS_FOR_CASE.format(case_id))

    try:
        citations = cursor_cited.fetchall()
        if len(citations) > 0:
            return [c[0] for c in citations]
        else:
            return []
    finally:
        cursor_cited.close()


def get_titles(case_id):
    cnx = get_connection()
    cursor = cnx.cursor()

    try:
        cursor.execute(T2_SELECT_TITLES_FOR_CASE.format(case_id))
        titles = cursor.fetchall()
        return [t[0] for t in titles]
    finally:
        cursor.close()


def task1_generator():
    cnx = get_connection()

    cursor = cnx.cursor()
    cursor.execute(T1_SELECT_CASES)
    cases = cursor.fetchall()
    res = [c[0] for c in cases]

    cursor.close()

    return res


def t2_save_case_db(case_id, noticed_id, entailed_frag, entailing_parags):
    save_case_db(case_id, 't2', noticed_id, entailed_frag, entailing_parags)


def t1_save_case_db(case_id):
    save_case_db(case_id, 't1')


def save_case_db(case_id, task_type, noticed_id=None, entailed_frag=None, entailing_parags=None):
    task_type = task_type.lower()
    if task_type not in ['t1', 't2']:
        raise ValueError('Invalid task type: {}'.format(task_type))

    cnx = get_connection()
    cursor = cnx.cursor()

    try:
        if task_type == 't1':
            ins_stmt = 'INSERT INTO prepared_t1 (base_id, prep_ts) VALUES (?, datetime(\'now\'))'
            cursor.execute(ins_stmt, (case_id, ))
        elif task_type == 't2':
            ins_stmt = 'INSERT INTO prepared_t2 \
                            (base_id, noticed_id, entailed_frag,entailing_parags, prep_ts) \
                            VALUES \
                            (?,?,?,?, datetime(\'now\'))'
            cursor.execute(ins_stmt, (case_id, noticed_id, entailed_frag,
                                      None if entailing_parags is None else str(entailing_parags).replace('[', '')
                                      .replace(']', '')))
        cnx.commit()
    finally:
        cursor.close()
        pass


def get_prepared_t1():
    cnx = get_connection()
    cursor = cnx.cursor()

    try:
        cursor.execute(T1_SELECT_PREPARED_CASES)
        cases = cursor.fetchall()
        return [c[0] for c in cases]
    finally:
        cursor.close()


def get_prepared_t2():
    cnx = get_connection()
    cursor = cnx.cursor()

    try:
        cursor.execute(T2_SELECT_PREPARED_CASES)
        cases = cursor.fetchall()
        return [(c[0], c[1], c[2], c[3], c[4]) for c in cases]
    finally:
        cursor.close()


def has_valid_citations(case_id, min_valid_citations):
    citations = get_cited_by(case_id, None)
    if len(citations) < min_valid_citations:
        return False

    valid_citations = 0
    for c in citations:
        html_filepath = cfu.find_case_contents_path(c)
        if os.path.exists(html_filepath) and not os.path.isdir(html_filepath) \
                and len(cfu.get_inner_text(html_filepath)) > 100:
            valid_citations = valid_citations + 1

        if valid_citations >= min_valid_citations:
            return True

    return False
