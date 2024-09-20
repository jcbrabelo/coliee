from bs4 import BeautifulSoup
import os
import re
from google.cloud import storage

GCLOUD_PROJECT_ID = 'coliee-data'
GCLOUD_BUCKET = 'coliee-files'
# INPUT_DIR = '/Users/jrabelo/Documents/coliee2020/Compass Federal Court Cases/HTML files'
    

def get_inner_text(html_filepath):
    contents = get_file_contents(html_filepath)

    soup = BeautifulSoup(contents, features="html.parser")
    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()  # rip it out

    # get text
    text = soup.get_text()

    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = "\n".join(chunk for chunk in chunks if chunk)

    return text


def find_pattern_in_text(pattern, string):
    refs = []
    if pattern is not None:
        occurs = re.finditer(pattern, string)
        for occur in occurs:
            refs.append((occur.start(), occur.end()))

    return refs


def filter_case_id(case_id):
    return case_id.split(':')[0]


def get_file_contents(file_path: str) -> str:
    storage_client = storage.Client(project=GCLOUD_PROJECT_ID)

    bucket = storage_client.bucket(GCLOUD_BUCKET)
    blob = bucket.blob(file_path)
    contents = blob.download_as_bytes()

    return contents.decode("utf-8")


def find_case_contents_path(case_id):
    case_id = filter_case_id(case_id)
    case_folder = f'files/{case_id}'

    storage_client = storage.Client(project=GCLOUD_PROJECT_ID)
    blobs = storage_client.list_blobs(GCLOUD_BUCKET, prefix=case_folder)
    for blob in blobs:
        if blob.name.lower().count('content') > 0:
            return blob.name
    
    return None


if __name__ == '__main__':
    case_path = find_case_contents_path("r06opoy8bfqbm")
    print(get_inner_text_from_string(get_file_contents(case_path)))
