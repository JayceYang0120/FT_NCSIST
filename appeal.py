import os
import re
import json
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

from utility import reader_txt, reader_json, write_output, get_html, get_query, get_content, get_head

from tqdm import tqdm
from bs4 import BeautifulSoup

def get_dict_history(case: dict) -> dict:
    """
    args:
        -case: dict, a case from the history list, 
            e.g.,{"desc":"臺灣基隆地方法院 89 年度 勞訴 字第 1 號判決(89.02.25)","href":"data.aspx?ty=JD&id=KLDV%2c89%2c%e5%8b%9e%e8%a8%b4%2c1%2c20000225","red":0}
    returns:
        -dict_link: dict, contains keys: text, link, link2json, link2web
    """
    pointer_null = False
    link = None
    link2json = None
    link2web = None
    text = case["desc"]

    if not case["href"]:
        pointer_null = True
    else:
        url_splitted = case["href"].split("id=")
        url_JID = url_splitted[1]
        JID = urllib.parse.unquote(url_splitted[1])

    if pointer_null:
        link = None
        link2json = None
        link2web = None
    else:
        link = URL_JUDICIAL + url_JID
        link2json = JID
        link2web = URL_JUDICIAL + JID
    return {
        "text": text,
        "link": link,
        "link2json": link2json,
        "link2web": link2web
    }

def get_dict_law(case: dict) -> dict:

    pattern_name = re.compile(r"(?P<law>.+?)(?=\s*第)")
    pattern_no = re.compile(r"(?<=第)\s*(?P<arts>.+?)\s*(?=條)")
    pattern_time = re.compile(r"([（(](?P<date>[0-9０-９]{2,3}\.\d{1,2}\.\d{1,2})[）)])")
    pointer_null = False
    law_name = None
    law_no = None
    law_time = None

    text = case["desc"]
    if not text:
        pointer_null = True
    else:
        match_name = pattern_name.search(text)
        match_no = pattern_no.search(text)
        match_time = pattern_time.search(text)
        name = match_name.group("law") if match_name else None
        no = match_no.group("arts") if match_no else None
        time = match_time.group("date") if match_time else None
        ### check region
        if not name:
            print(f"Warning: no law name found. text: {text}")
        if name and not no:
            print(f"Warning: law name found but no article number. text: {text}")
        if no and not name:
            print(f"Warning: article number found but no law name. text: {text}")
        ### check region
    if pointer_null:
        law_name = None
        law_no = None
        law_time = None
    else:
        law_name = name
        law_no = no
        law_time = time

    return {
        "law_name": law_name,
        "law_no": law_no,
        "law_time": law_time
    }

def find_history(file: str) -> list:
    """
    datatype in list_history: json, each json object is like:
    {
        "text": str,
        "link": str,
        "link2json": str,
        "link2web": str
    }
    args:
        -file, str, JID
    returns:
        -list_history: list, each element is a dict with keys: text, link, link2json, link2web
    """
    list_history = []

    text_raw_html = get_html(file)

    tuple_history = get_query(
        raw_html = text_raw_html,
        pattern = r"\"\.\./controls/GetJudHistory\.ashx\?jid=.*\"",
    )
    dict_history = json.loads(tuple_history[1]) if tuple_history[1] else {}

    if "count" not in dict_history.keys():
        print(f"Warning: 'count' key not found in history for JID: {file}")
        return list_history

    if dict_history["count"]:
        for case in dict_history['list']:
            dict_link = get_dict_history(case)
            list_history.append(dict_link)

    return list_history

def find_law(file: str) -> list:
    """
    datatype in list_law: json, each json object is like:
    {
        "law_name": str,
        "law_no": str,
        "law_time": str
    }
    args:
        -file, str, JID
    returns:
        -list_law: list, each element is a dict with keys: law_name, law_no, law_time
    """
    list_law = []
    pointer_fail = False

    exception_list = ["TPSV,111,台聲,2042,20220922,1"] # this JID return error related law
    if file in exception_list:
        return list_law, pointer_fail

    text_raw_html = get_html(file)
    time.sleep(0.5)
    tuple_related_law = get_query(
        raw_html = text_raw_html,
        pattern = r"\"\.\./controls/GetJudRelatedLaw\.ashx\?pkid=.*\"",
    )
    dict_related_law = json.loads(tuple_related_law[1]) if tuple_related_law[1] else {}

    if "count" not in dict_related_law.keys():
        pointer_fail = True
        # print(f"Warning: 'count' key not found in related law for JID: {file}")
        return list_law, pointer_fail

    if dict_related_law["count"]:
        for case in dict_related_law['list']:
            dict_law = get_dict_law(case)
            list_law.append(dict_law)

    return list_law, pointer_fail

def find_loop(file: str) -> list:
    """
    Solve the problem of related law retrieval failure is due to request of API.
    args:
        -file, str, JID
    returns:
        -list_law: list, each element is a dict with keys: law_name, law_no, law_time
    """
    list_law = []
    pointer_fail = True
    count_retry = 0
    patience = 50
    while pointer_fail and count_retry < patience:
        list_law, pointer_fail = find_law(file)
        count_retry += 1
    if count_retry >= patience:
        print(f"Warning: related law retrieval failed after patience retries for JID: {file}")
    return list_law

def fliter_new_jid(file: str) -> int:
    """
    filter JID to check if it is a secret case or not a judgment.
    args:
        -file: str, JID of the new case.
    returns:
        : int, indicating the status of the case:
            -  0 if it is a clean case
            -  1 if it is a secret case
            -  2 if it is not a judgment
            - -1 if content not found.
    """
    class_name_content = "text-pre text-pre-in"
    class_name_content_2 = "htmlcontent"
    class_name_col_th = "col-th"
    class_name_col_td = "col-td"
    pattern_secret = r"本件經程式判定為依法不得公開或須去識別化後公開之案件"
    pattern_head = r"裁判字號"
    pattern_judgment = r"判決"
    pattern_court = r"最高法院"

    text_HTML = get_html(file)
    soup = BeautifulSoup(text_HTML, "html.parser")
    content = get_content(soup, class_name_content)
    len_content = len(content)
    if len_content == 0:
        content = get_content(soup, class_name_content_2)
        len_content = len(content)
    if content == "-1":
        print(f"Content not found or class name does not match. JID: {file}")
        return -1
    if (len_content < 15):
        print(f"Content too short, length: {len_content}. JID: {file}")
        return -1
    len_content_min = min(len_content, 500)
    content_front = content[:len_content_min]
    if re.search(pattern_secret, content_front):
        return 1
    text_head = get_head(soup, class_name_col_th, class_name_col_td, pattern_head)
    if not re.search(pattern_judgment, text_head):
        if not re.search(pattern_court, text_head):
            return 2
    return 0

def extend_history(list_history_original: list, set_original_jid: set) -> list:
    """
    Extend the history of cases by checking if the JID in history is already in the original set.
    args:
        -list_history_original: list, a list of dictionaries containing history information.
        -set_original_jid: set, a set of original JIDs to check against.
    returns:
        -list_new_history: list, a list of dictionaries with new JIDs and their history.
    """
    list_new_history = []

    for item in tqdm(list_history_original, desc = "Extending history"):
        jid = item["JID"]
        history = item["history"]
        if not history: # size of empty = 154
            continue
        for judgment in history:
            hist_jid = judgment.get("link2json", None)
            if hist_jid and (hist_jid not in set_original_jid):
                dict_temp = {
                    "JID": hist_jid,
                    "history": history,
                }
                list_new_history.append(dict_temp)
                set_original_jid.add(hist_jid)

    return list_new_history

def appeal():

    """
    description:
    1. request judicial website to get the history of each case
    2. extend dataset from history
    3. filtering out cases based on value of "int_case", which is returned by fliter_new_jid function
    4. merging all history and sorting then save
    5. dataset size description
    """

    ### parameters for step 1.
    files_list_judgment = f'./logs/filtering/files_list_judgment.txt'
    files_list_no_judgment_SV = f'./logs/filtering/files_list_no_judgment_SV.txt'
    output_path_link = f'./appeal/origin_history.jsonl'
    ### parameters for step 1.

    ### parameters for step 2.
    output_path_new_history = f'./logs/appealing/new_history.txt'
    ### parameters for step 2.

    ### parameters for step 3.
    output_path_new_history_cleaned = f'./appeal/new_history_cleaned.jsonl'
    output_path_file_new_history_cleaned = f'./logs/appealing/new_history_cleaned.txt'
    output_path_file_new_history_secret = f'./logs/appealing/new_history_secret.txt'
    output_path_file_new_history_no_judgment = f'./logs/appealing/new_history_no_judgment.txt'
    output_path_file_new_history_invalid = f'./logs/appealing/new_history_invalid.txt'
    ### parameters for step 3.

    ### parameters for step 4.
    output_path_all_links = f'./appeal/all_history.jsonl'
    output_path_all_links_file = f'./logs/appealing/all_history.txt'
    ### parameters for step 4.

    #### variable for global variables
    global URL_JUDICIAL
    URL_JUDICIAL = "https://judgment.judicial.gov.tw/FJUD/data.aspx?ty=JD&id="
    MAX_WORKERS = 10
    #### variable for global variables

    """
    step 1. request judicial website to get the history of each case
    """
    list_files_list = []
    list_output = []
    list_history_temp = {}
    list_law_temp = {}
    count_case_history = 0
    count_case_law = 0
    """
    datatype of output file from list_output: jsonl, each json object is like:
    {
    "JID": str,
    "history": list,
    "related_law": list
    }
    """

    list_files_list = reader_txt(files_list_judgment) + reader_txt(files_list_no_judgment_SV)

    if not os.path.exists(output_path_link):
        with ThreadPoolExecutor(max_workers = MAX_WORKERS) as executor:
            futures = {executor.submit(find_law, file): file for file in list_files_list}
            for future in tqdm(as_completed(futures), total = len(futures), desc = "Processing related law"):
                try:
                    file = futures[future]
                    list_law, pointer_fail = future.result()
                    if pointer_fail:
                        list_law = find_loop(file)
                    list_law_temp[file] = list_law
                    count_case_law += 1
                    if count_case_law % 30 == 0:
                        time.sleep(2)
                except Exception as e:
                    print(f"Error processing {file}: {e}")
        with ThreadPoolExecutor(max_workers = MAX_WORKERS) as executor:
            futures = {executor.submit(find_history, file): file for file in list_files_list}
            for future in tqdm(as_completed(futures), total = len(futures), desc = "Processing history"):
                try:
                    file = futures[future]
                    list_history = future.result()
                    list_history_temp[file] = list_history
                    count_case_history += 1
                    if count_case_history % 30 == 0:
                        time.sleep(2)
                except Exception as e:
                    print(f"Error processing {file}: {e}")
        for file in list_files_list:
            list_history = list_history_temp[file]
            list_law = list_law_temp[file]
            dict_temp = {
                "JID": file,
                "history": list_history,
                "related_law": list_law
            }
            list_output.append(dict_temp)
        write_output(list_output, output_path_link)

    """
    step 2. extend dataset from history
    """
    path_link = output_path_link
    set_original_jid = set(list_files_list)
    
    list_history_original = reader_json(path_link)

    list_new_history = extend_history(list_history_original, set_original_jid)
    list_file_new_history = [item["JID"] for item in list_new_history]
    write_output(list_file_new_history, output_path_new_history)

    """
    step 3. filtering out cases based on value of "int_case", which is returned by fliter_new_jid function
    """
    count_case = 0
    list_new_history_cleaned = []
    list_file_new_history_cleaned = []
    list_file_new_history_secret = []
    list_file_new_history_no_judgment = []
    list_file_new_history_invalid = []

    if not os.path.exists(output_path_new_history_cleaned):
        with ThreadPoolExecutor(max_workers = MAX_WORKERS) as executor:
            futures = {executor.submit(fliter_new_jid, item["JID"]): item for item in list_new_history}
            for future in tqdm(as_completed(futures), total = len(futures)):
                try:
                    item = futures[future]
                    int_case = future.result()
                    if int_case == 0:
                        counter_retry = 0
                        list_law, pointer_fail = find_law(item["JID"])
                        if pointer_fail:
                            list_law = find_loop(item["JID"])
                        item["related_law"] = list_law
                        list_new_history_cleaned.append(item)
                        list_file_new_history_cleaned.append(item["JID"])
                    elif int_case == 1:
                        list_file_new_history_secret.append(item["JID"])
                    elif int_case == 2:
                        list_file_new_history_no_judgment.append(item["JID"])
                    else:
                        list_file_new_history_invalid.append(item["JID"])
                    count_case += 1
                    if count_case % 30 == 0:
                        time.sleep(2)
                except Exception as e:
                    e_jid = item["JID"]
                    print(f"Error processing {e_jid}: {e}")

        write_output(list_new_history_cleaned, output_path_new_history_cleaned)
        write_output(list_file_new_history_cleaned, output_path_file_new_history_cleaned)
        write_output(list_file_new_history_secret, output_path_file_new_history_secret)
        write_output(list_file_new_history_no_judgment, output_path_file_new_history_no_judgment)
        write_output(list_file_new_history_invalid, output_path_file_new_history_invalid)
    
    """
    step 4. merging all history and sorting then save
    """
    list_all_history = []
    list_file_all_history = []

    list_history_cleaned = reader_json(output_path_new_history_cleaned)
    merged_list_history = list_history_original + list_history_cleaned
    for item in merged_list_history:
        version = item["JID"].split(",")
        if len(version) > 5:
            item["version"] = version[5]
        else:
            item["version"] = "0"
    merged_list_history.sort(key = lambda x: (x["JID"].split(",")[4], x["version"]))

    for instance_json in merged_list_history:
        JID = instance_json["JID"]
        history = instance_json["history"]
        related_law = instance_json["related_law"]
        list_file_all_history.append(JID)
        list_all_history.append({
            "JID": JID,
            "history": history,
            "related_law": related_law
        })

    write_output(list_all_history, output_path_all_links)
    write_output(list_file_all_history, output_path_all_links_file)

    """
    step 5. dataset size description
    """
    print(f"Total cases processed: {len(list_files_list)}")
    print(f"Total new history cases found before cleaning: {len(list_new_history)}")
    print(f"Total new history cases after cleaning: {len(list_history_cleaned)}")
    if len(list_file_new_history_no_judgment) != 0:
        print(f"Total secret cases: {len(list_file_new_history_secret)}")
        print(f"Total no judgment cases: {len(list_file_new_history_no_judgment)}")
        print(f"Total invalid cases: {len(list_file_new_history_invalid)}")
    print(f"Total history found: {len(list_all_history)}")

if __name__ == "__main__":
    appeal()