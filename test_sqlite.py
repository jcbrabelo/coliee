import sqlite3


SELECT_CITATIONS_FOR_CASE = "SELECT c.id FROM citations cit, cases c \
            where cit.caseid = '{}' and cit.cited_URI_vlex = c.URI_vlex and cit.cited_URI_vlex is not null \
            and cit.caseid <> c.id"


def get_cited_by(case_id, cnx):
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


if __name__ == '__main__':

    con = sqlite3.connect("coliee.db")
    cursor_cited = con.cursor()
    cursor_cited.execute("select datetime('now')")
    res = cursor_cited.fetchone()
    print(res[0])

    con.close()
