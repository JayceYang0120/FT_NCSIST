import os
import json
import regex as re
from concurrent.futures import ProcessPoolExecutor, as_completed

import rarfile
from tqdm import tqdm

from utility import write_output, write_json

def get_court(file_name: str) -> str:
    """
    Extract court code from the file name.
    args:
        file_name: str, JID of the file.
    returns:
        court: str, The extracted court .
    """
    pattern_court = re.compile(r"TYDV|TYEV|CLEV|HV|SV")
    match_court = pattern_court.search(file_name)
    return match_court.group(0) if match_court else ""

def filter_file(file_name: str) -> bool:
    """
    NCSIST condition for filtering files
    114-08-27
    1. 桃園地方法院 (TYDV)
    2. 桃園簡易庭 (TYEV)
    3. 中壢簡易庭 (CLEV)
    """
    # inclusion_court = "TYDV|TYEV|CLEV|HV|SV" # EV: 簡易庭, DV: 地方法院, HV: 高等法院, SV: 最高法院
    if not file_name.endswith(".json"):
        return True
    if not get_court(file_name):
        return True
    return False

def filter_JTITLE(title: str) -> bool:
    inclusion = "退休"
    if not re.search(inclusion, title):
        return True
    return False

def filter_content(header: str) -> bool:
    exclusion = "裁定|附帶民事|宣示筆錄|筆錄"
    inclusion = "判決"
    if re.search(exclusion, header):
        return True
    if not re.search(inclusion, header):
        return True
    return False

def process_rar(doc, path_rar: str, output_path: str):

    results = {
        "counter_all": 0,
        "counter_judgment": 0,
        "counter_no_judgment": 0,
        "counter_no_judgment_SV": 0,
        "list_judgment": [],
        "list_no_judgment": [],
        "list_no_judgment_SV": []
    }

    file_path = os.path.join(path_rar, doc)
    with rarfile.RarFile(file_path) as rf:
        for fileinfo in rf.infolist():
            file_name = fileinfo.filename
            if filter_file(file_name): 
                continue
            JID = file_name.split("/")[-1].split(".")[0]
            court = get_court(file_name)
            with rf.open(file_name) as jf:
                json_data = json.load(jf)
            full_text_title = json_data['JTITLE']
            if filter_JTITLE(full_text_title): 
                continue
            results["counter_all"] += 1
            full_text_header = json_data['JFULL'].split('\n', 1)[0]
            if filter_content(full_text_header): 
                results["counter_no_judgment"] += 1
                results["list_no_judgment"].append(JID)
                if court != "SV":
                    continue
                results["counter_no_judgment_SV"] += 1
                results["list_no_judgment_SV"].append(JID)
            else:
                results["counter_judgment"] += 1
                results["list_judgment"].append(JID)
            output_file = os.path.join(output_path, f"{JID}.json")
            write_json(json_data, output_file)
    return results

def filter():

    ### parameters for common
    path_rar = '../Dataset/'
    ### parameters for common

    ### variables for common
    MAX_WORKERS = 8
    ### variables for common

    ### parameters for step 1.
    output_path = f'./assets_retire/'
    output_path_judgment = f'./logs/filtering/files_list_judgment.txt'
    output_path_no_judgment = f'./logs/filtering/files_list_no_judgment.txt'
    output_path_no_judgment_SV = f'./logs/filtering/files_list_no_judgment_SV.txt'
    ### parameters for step 1.

    ### variables for step 1.
    all_results = {
        "counter_all": 0,
        "counter_judgment": 0,
        "counter_no_judgment": 0,
        "counter_no_judgment_SV": 0,
        "list_judgment": [],
        "list_no_judgment": [],
        "list_no_judgment_SV": []
    }
    ### variables for step 1.

    """
    step 1. : filter the rar files based on conditions
    """
    if not os.path.exists(output_path_no_judgment) or not os.path.exists(output_path_judgment):
        with ProcessPoolExecutor(max_workers = MAX_WORKERS) as executor:
            futures = [executor.submit(process_rar, doc, path_rar, output_path) for doc in os.listdir(path_rar)]
            for future in tqdm(as_completed(futures), total = len(futures), desc = "Processing RAR files"):
                res = future.result()
                all_results["counter_all"] += res["counter_all"]
                all_results["counter_judgment"] += res["counter_judgment"]
                all_results["counter_no_judgment"] += res["counter_no_judgment"]
                all_results["counter_no_judgment_SV"] += res["counter_no_judgment_SV"]
                all_results["list_judgment"].extend(res["list_judgment"])
                all_results["list_no_judgment"].extend(res["list_no_judgment"])
                all_results["list_no_judgment_SV"].extend(res["list_no_judgment_SV"])
        print('counter_all:',  all_results["counter_all"]) # 案由包含"退休"的裁判書數量
        print('counter_judgment:', all_results["counter_judgment"]) # 案由包含"退休"的判決書數量
        print('counter_no_judgment:', all_results["counter_no_judgment"]) # 案由包含"退休"的非"判決"書數量
        print('counter_no_judgment_SV:', all_results["counter_no_judgment_SV"]) # 案由包含"退休"的非"判決"書數量中, 最高法院的數量
        """
        years > 200001 ~ 202503
        JTITLE > "退休"
        court > TYDV、TYEV、CLEV、HV、SV
        results:
            a. 裁判書: 3,934 件
            b. 判決書: 2,894 件
            c. 判決書以外: 1,040 件
            d. 判決書以外但屬於最高法院: 363 件 b.t.w, it is subset of c.
        useful > 2,894 + 363 = 3,257 件
        """
        write_output(all_results["list_judgment"], output_path_judgment)
        write_output(all_results["list_no_judgment"], output_path_no_judgment)
        write_output(all_results["list_no_judgment_SV"], output_path_no_judgment_SV)
    
if __name__ == '__main__':
    filter()