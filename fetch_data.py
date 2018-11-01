import requests
import json
import os
import time
from tqdm import tqdm
from html.parser import HTMLParser

global token_val


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

#this token is open api explorer's JWT_token
token_val='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJ1MDZwNnB4a204eXdlNHciLCJpYXQiOjE1NDA4MzM3Mjl9.QCSYhXT6UN-v3q7qTovB8IkLs9y19uAcGBRZcIL2N9Q'

def query_cite_by_id(case_id):
    """
    :param case_id: get this case id from  open api explorer's query result
    :return: list of vlex url's of noticed cases
    """
    headers = {
        'Origin': 'https://amii.icbg.io',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,fr;q=0.7,zh-TW;q=0.6',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'icebergauthtoken': token_val,
        'Connection': 'keep-alive',
    }

    data = '{"query":"query($workspaceId: ID, $filters: [SearchFilterInput]){\\n  viewer {\\n    records(first: 10, filters: $filters, asOf: $workspaceId) {\\n      edges {\\n        node {\\n          id\\n          label\\n          cites: outgoing(first: 100, instanceOf:\\"k9\\") { ... Fragment_RelationshipData}\\n        }\\n      }\\n    }\\n  }\\n}\\n\\nfragment Fragment_RelationshipData on RelationshipsWithTotalConnection {\\n  size\\n  edges {\\n    node {\\n      target {\\n        id\\n        uris\\n      }\\n    }\\n  }\\n}\\n\\n","variables":{"filters":{"hasId":"'+case_id+'"}}}'

    response = requests.post('https://amii.icbg.io/graphql', headers=headers, data=data)
    noticed_cases = [(elem['node']['target']['id'], elem['node']['target']['uris'][0]) for elem in response.json()['data']['viewer']['records']['edges'][0]['node']['cites']['edges']]
    return noticed_cases

def request_case_headnote_content(case_id):
    """
    :param case_id: get this case id from  open api explorer's query result
    :return: content + headnote + original json response
    """
    headers = {
        'Content-Type': 'application/json',
        'icebergauthtoken': token_val,
        'Connection': 'keep-alive',
    }

    data = '{"id":"q77","query":"query NodeQueries($id_0:ID!) {node(id:$id_0) {id,__typename,...F4}} fragment F0 on PropertyValue {timestamp,ref,id,commited,data {components {key,value},dataType,deleted,locale,label,sortValue,qualityScore,value,mediaObject {id,fileFormat,contentURL,contentSizeBytes}},property {id},ref} fragment F1 on Instance {id,propertiesInDomain {id,name,dataTypes},_propertyValuesVZeVI:propertyValues(includeSystemProperties:true) {ref,property {id,name},data {sortValue,dataType},id,...F0},__typename} fragment F2 on Node {id,__typename,...F1} fragment F3 on Record {id,deleted,classes {id},hasUncommitedEdits,hasUnmergedEdits,label,...F2} fragment F4 on Node {id,__typename,...F3}","variables":{"id_0":"'+case_id+'"}}'
    response = requests.post('https://amii.icbg.io/graphql', headers=headers, data=data)
    ret_json = {}
    try:
        resp_json = response.json()
        for elem in resp_json['data']['node']['_propertyValuesVZeVI']:
            if elem['data']['dataType'] == 'MEDIA':
                media_url = elem['data']['mediaObject']['contentURL']
                ret_json[elem['property']['name']] = requests.get(media_url).text
        resp = [ret_json, response.text]
        return ret_json, response.text
    except ValueError as e:
        print("None Json Request")
        return None, None

def fetch_store (from_file, to_folder):
    file = open(from_file, 'r')
    doc = json.load(file)
    nodes = doc['data']['viewer']['records']['edges']
    print(len(nodes))
    for node in nodes:
        id = node['node']['id']
        label = node['node']['label']
        id_path = os.path.join(to_folder, id)
        if not os.path.exists(id_path):
            print('Fetching contents for id ', id)
            contents, json_resp = request_case_headnote_content(id)
            print('Writing to disk contents for id ', id)
            store_case_contents(id, id_path, contents, json_resp)
                
            time.sleep(1)

        else:
            print('Folder already exists: ', id)
        
    file.close()


def store_contents(id, id_path, contents, json_resp):
    if not os.path.exists(id_path):
        os.makedirs(id_path)

    with open(os.path.join(id_path, "contents.html"), "w") as content_file:
        if contents is not None and contents.get('content') is not None:
            content_file.write(contents['content'])
        else:
            print('No contents for id ', id)
            content_file.write('')

    with open(os.path.join(id_path, "headnotes.html"), "w") as headnotes_file:
        if contents is not None and contents.get('headnotes') is not None:
            headnotes_file.write(contents['headnotes'])
        else:
            print('No headnotes for id ', id)
            headnotes_file.write('')

    with open(os.path.join(id_path, "response.json"), "w") as json_file:
        if json_resp is not None:
            json_file.write(json_resp)
        else:
            json_file.write('')
            

def fetch_cited(src_folder):
    for src_id in os.listdir(src_folder):
        if src_id.startswith('.'):
            continue

        print('Processing ', src_id)
        cited_filepath = os.path.join(src_folder, src_id, 'cites.txt')
        if not os.path.exists(cited_filepath):
            with open(cited_filepath, 'w') as cited_file:
                cited_list = query_cite_by_id(src_id)
                for cited_id, uri in cited_list:
                    cited_file.write(cited_id+','+uri+'\n')

                cited_file.write('\n')
                time.sleep(1)
        else:
            print('Cited case IDs already fetched for id '+src_id)

        print('Downloading contents')

        with open(cited_filepath, 'r') as cited_file:
            lines = cited_file.readlines()
            for line in lines:
                if len(line) < 5:
                    continue

                parts = line.split(',')
                cited_id = parts[0]
                if len(cited_id) < 20:
                    id_path = os.path.join(src_folder, cited_id) 
                    if not os.path.exists(os.path.join(id_path, "contents.html")):
                        contents, json_resp = request_case_headnote_content(cited_id)
                        store_contents(cited_id, id_path, contents, json_resp)
                    else:
                        print('Contents already exist for id ',cited_id)
                else:
                    print('skipping id ',cited_id)


def parse_html_folder(html_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for src_folder in os.listdir(html_folder):
        if src_folder.startswith('.'):
            continue

        print('Processing ',src_folder)
        content_filepath = os.path.join(html_folder, src_folder, 'contents.html')
        headnotes_filepath = os.path.join(html_folder, src_folder, 'headnotes.html')
        if os.path.exists(content_filepath):
            with open(content_filepath, 'r') as cont_file:
                raw_contents = cont_file.read()
                parser = ColieeHTMLParser()
                parser.feed(raw_contents)
                contents = parser.get_text()
                parser.close()

            headnotes = ''
            if os.path.exists(headnotes_filepath):
                with open(headnotes_filepath, 'r') as head_file:
                    raw_headnotes = head_file.read()
                    parser = ColieeHTMLParser()
                    parser.feed(raw_headnotes)
                    headnotes = parser.get_text()
                    parser.close()

            txt_file = os.path.join(output_folder, src_folder+'.txt')
            with open (txt_file, 'w') as txt_file:
                txt_file.write(headnotes + '\n' +contents)

        
if __name__ == '__main__':
    #query_cite_by_id('r06p2ygc993ea1w')
    #json, txt = request_case_headnote_content('r06p2ygc993ea1w')
    #print(json)
    #print(' ---------------------  ')
    #print (txt)

    #fetch_store('/Users/administrator/Documents/coliee2019/data_fetch/4000_5000.json','/Users/administrator/Documents/coliee2019/data_fetch/files')

    #parse_html_folder('/Users/administrator/Documents/coliee2019/data_fetch/files', '/Users/administrator/Documents/coliee2019/data_fetch/txt')

    fetch_cited('/Users/administrator/Documents/coliee2019/data_fetch/files')

    '''
    contents, json_resp = request_case_headnote_content('UaHR0cDovL3ZsZXguY29tL3ZpZC82ODE2NzExMDU=')

    p = ColieeHTMLParser()
    p.feed(contents['content'])
    print(p.get_text())

    p = ColieeHTMLParser()
    p.feed(contents['headnotes'])
    print(p.get_text())

    p.close()
      '''