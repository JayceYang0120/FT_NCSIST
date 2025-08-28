import os
import re
import json
import argparse

from bs4 import BeautifulSoup
from tqdm import tqdm

from utility import reader_txt, reader_json, write_output, get_html, get_content, get_head

def filter_empty_history(list_judgments: list) -> tuple:
    """
    args:
        - list_judgments: list, the list of judgments to filter.
    returns:
        : tuple, containing:
            - list_judgments_non_empty: list, judgments with non-empty history.
            - list_judgments_empty: list, judgments with empty history.
    """
    list_judgments_non_empty = []
    list_judgments_empty = []

    for judgment in tqdm(list_judgments, desc="Filtering Empty History"):
        if judgment['history']:
            list_judgments_non_empty.append(judgment)
        else:
            list_judgments_empty.append(judgment['JID'])

    return list_judgments_non_empty, list_judgments_empty

def filter_history_jid(jid: str) -> int:
    """
    args:
        -jid: str, JID of the new history.
    returns:
        : int, indicating the status of the case:
            -  0 if it is a clean case
            -  1 if it is a secret case (second)
            -  2 if it is not a judgment (first > step 2.)
            - -1 if content not found.
    """
    class_name_content = "text-pre text-pre-in"
    class_name_col_th = "col-th"
    class_name_col_td = "col-td"
    pattern_secret = r"本件經程式判定為依法不得公開或須去識別化後公開之案件"
    pattern_head = r"裁判字號"
    pattern_no_judgment = r"裁定|筆錄" # 檢查過不存在"判決筆錄"
    
    text_HTML = get_html(jid)
    soup = BeautifulSoup(text_HTML, "html.parser")
    text_head = get_head(soup, class_name_col_th, class_name_col_td, pattern_head)
    if re.search(pattern_no_judgment, text_head):
        return 2
    content = get_content(soup, class_name_content)
    if content == "-1":
        print("Content not found or class name does not match.")
        return -1
    len_content_min = min(len(content), 1000)
    content_front = content[:len_content_min]
    if re.search(pattern_secret, content_front):
        return 1
    return 0

def filter_decision(list_judgments_non_empty_history: list) -> tuple:
    """
    args:
        - list_judgments_non_empty_history: list, the list of judgments with non-empty history, including unknown text.
    returns:
        : tuple, containing:
            - list_judgments_filtered: list, judgments with filtered histories.
            - list_history_decision: list, judgments with decision history.
    """
    list_judgments_filtered = []
    list_history_decision = [] # 不論甚麼情形都會丟

    for judgment in tqdm(list_judgments_non_empty_history, desc = "Filtering Decision History"):
        jid = judgment['JID']
        histories = judgment['history']
        histories_filtered = []
        histories_decision = {
            "JID": jid,
            "history": []
        }
        for history in histories:
            jid_history = history.get("link2json", None)
            text = history.get("text", None)
            if jid_history:
                int_case = filter_history_jid(jid_history)
                if int_case == 2:
                    histories_decision['history'].append(history)
                    continue
                history['int_case'] = int_case
                histories_filtered.append(history)
            else:
                if "裁定" in text or "筆錄" in text:
                    histories_decision['history'].append(history)
                    continue
                history['int_case'] = None
                histories_filtered.append(history)

        if histories_decision['history']:
            list_history_decision.append(histories_decision)

        if histories_filtered:
            judgment['history'] = histories_filtered
            list_judgments_filtered.append(judgment)
        else:
            if not histories_decision['history']:
                print(f"Warning: No valid history for JID {jid}.")

    return list_judgments_filtered, list_history_decision

def filter_useless_link(list_link_wo_filter: list) -> tuple:
    """
    args:
        - list_link_wo_filter: list, the list of judgments with links without filtering.
    returns:
        : tuple, containing:
            - list_link_filtered: list, judgments with useful links.
            - list_link_useless: list, judgments with useless links.
    """
    list_link_filtered = []
    list_link_useless = []

    for judgment in tqdm(list_link_wo_filter, desc="Filtering Useless Links"):
        pointer = False
        pointer_last = False
        histories_filtered = []
        threshold = 1
        jid = judgment['JID']
        histories = judgment['history']
        for index, history in enumerate(histories):
            int_case = history["int_case"]
            if int_case is None or int_case == 1: # None means no link2json, 1 means secret case
                if index != len(histories) - 1:
                    pointer = True
                    break
                else:
                    if len(histories_filtered) <= 1:
                        pointer = True
                    histories_filtered.append(history)
                    pointer_last = True
            else:
                histories_filtered.append(history)
        if pointer_last:
            threshold = 2
        if len(histories_filtered) <= threshold:
            pointer = True
        if pointer:
            list_link_useless.append(judgment)
        else:
            judgment['history'] = histories_filtered
            list_link_filtered.append(judgment)

    return list_link_filtered, list_link_useless

def get_link_text(text: str) -> str:
    """
    args:
        - text: str, the text content of the history.
    returns:
        : str, the court text.
    """
    pattern_detail = re.compile(r"(?:臺灣|台灣)?(.{1,30}) \s*\d{2,3}\s*年") # notice space before \s*
    pattern_overall = re.compile(r"(簡易庭|地方法院|高等法院|最高法院)[^0-9]{0,20}?\d{2,3}\s*年")

    match_detail = re.search(pattern_detail, text)
    match_overall = re.search(pattern_overall, text)
    text_detail = match_detail.group(1) if match_detail else "Unknown Court"
    text_detail_splited = text_detail.split(" ")
    if len(text_detail_splited) > 1:
        text_detail = "".join(text_detail_splited)
    if match_detail and match_overall:
        return text_detail, match_overall.group(1)
    print(f"Warning: No court found in text: {text}")
    return "Unknown Court"

def linking_history(list_judgments_filtered: list) -> list:
    """
    args:
        - list_judgments_filtered: list, the list of judgments with filtered histories.
    returns:
        - list_judgments_link: list, the list of judgments with linked histories.
    """
    list_judgments_link = []

    for judgment in tqdm(list_judgments_filtered, desc="Linking Judgments"):
        jid = judgment['JID']
        histories = judgment['history']
        if not histories:
            raise ValueError(f"No histories found for JID {jid}.")
        str_link_detail = ""
        str_link_overall = ""
        for history in histories:
            text = history.get("text", None)
            court_detail, court_overall = get_link_text(text)
            str_link_detail = f"{str_link_detail}_{court_detail}"
            str_link_overall = f"{str_link_overall}_{court_overall}"
        judgment["link_detail"] = str_link_detail.strip("_")
        judgment["link_overall"] = str_link_overall.strip("_")
        list_judgments_link.append(judgment)

    return list_judgments_link

def analysis(list_judgments: list, priority: str) -> tuple:
    """
    args:
        - list_judgments: list, the list of judgments to analyze.
        - priority: str, the priority for analysis, either "frequency" or "length".
    returns:
        : tuple, containing:
            - sorted_links_overall: list, sorted links based on overall court frequency or length.
            - sorted_links_detail: list, sorted links based on detail court frequency or length.
    """
    dict_link_overall = {}
    dict_link_detail = {}
    sorted_links_overall = []
    sorted_links_detail = []
    
    for judgment in list_judgments:
        link_overall = judgment["link_overall"]
        link_detail = judgment["link_detail"]
        if link_overall not in dict_link_overall:
            dict_link_overall[link_overall] = 1
        else:
            dict_link_overall[link_overall] += 1

        if link_detail not in dict_link_detail:
            dict_link_detail[link_detail] = 1
        else:
            dict_link_detail[link_detail] += 1

    if priority == "frequency":
        sorted_links_overall = sorted(dict_link_overall.items(), key = lambda x: x[1], reverse = True)
        sorted_links_detail = sorted(dict_link_detail.items(), key = lambda x: x[1], reverse = True)
    else:
        sorted_links_overall = sorted(dict_link_overall.items(), key = lambda x: len(x[0]), reverse = True)
        sorted_links_detail = sorted(dict_link_detail.items(), key = lambda x: len(x[0]), reverse = True)
        
    return sorted_links_overall, sorted_links_detail

def link():
    
    parser = argparse.ArgumentParser(description = "Linking judgments based on their histories")
    
    parser.add_argument('--dir_name', type = str, default = "retire", help = 'Input retire|labor (default: "retire")')
    
    args = parser.parse_args()

    dir_name = args.dir_name

    """
    script description:
    著重在若有上訴的情形發生，連結判決書之間的關係。
    1. filtering empty history
    2. filtering decision or no judgment in history, so would change the dictionary structure
        pseudo code:
        set list cleaned_histories to put history should be linked
        for history in histories:
            if link2json:
                get_html > 2 cases:
                    1. open case > filtering decision or no judgment (筆錄) in history, else remaining and extend
                    2. secret case > filtering decision or no judgment (筆錄) in history, else remaining and extend
            else:
                filtering decision or no judgment (筆錄) in history, else remaining and extend
    3. linking the judgments between histories
    4. analyzing the linking results
    5. filtering jid == null or secret case (but exception existing)
        a. if it is last history and length of histories_filtered > 1, remaining and extend, so output would include int_case = 1 or int_case = None
    6. analyzing the linking result with flitering useless judgments
    7. description size of each steps
    """

    ### parameters for step 1.
    path_unique_judgments = f'./unique/{dir_name}/unique_history.jsonl'
    output_path_judgments_empty_history = f'./unique/{dir_name}/judgments_empty_history.txt'
    ### parameters for step 1.

    ### parameters for step 2.
    output_path_judgments_filtered = f'./unique/{dir_name}/judgments_filtered.jsonl'
    output_path_judgments_decision_filter = f'./unique/{dir_name}/decision_history.jsonl'
    ### parameters for step 2.
    
    ### parameters for step 3.
    output_path_judgments_link = f'./links/{dir_name}/link_wo_filter.jsonl'
    ### parameters for step 3.

    ### parameters for step 4.
    output_path_analyze_freq = f'./links/{dir_name}/analyze_overall_freq_wo_filter.txt'
    output_path_analyze_length = f'./links/{dir_name}/analyze_overall_length_wo_filter.txt'
    output_path_analyze_freq_detail = f'./links/{dir_name}/analyze_detail_freq_wo_filter.txt'
    output_path_analyze_length_detail = f'./links/{dir_name}/analyze_detail_length_wo_filter.txt'
    ### parameters for step 4.
    
    ### parameters for step 5.
    output_path_judgments_link_filtered = f'./links/{dir_name}/link_filtered.jsonl'
    output_path_judgments_link_useless = f'./links/{dir_name}/link_useless.jsonl'
    ### parameters for step 5.
    
    ### parameters for step 6.
    output_path_analyze_freq_filtered = f'./links/{dir_name}/analyze_overall_freq_filtered.txt'
    output_path_analyze_length_filtered = f'./links/{dir_name}/analyze_overall_length_filtered.txt'
    output_path_analyze_freq_detail_filtered = f'./links/{dir_name}/analyze_detail_freq_filtered.txt'
    output_path_analyze_length_detail_filtered = f'./links/{dir_name}/analyze_detail_length_filtered.txt'
    ### parameters for step 6.

    """
    step 1. filtering empty history
    """
    list_unique_judgments = reader_json(path_unique_judgments)

    list_judgments_non_empty_history, list_file_judgments_empty_history = filter_empty_history(list_unique_judgments)
    
    write_output(list_file_judgments_empty_history, output_path_judgments_empty_history)

    """
    step 2. filtering decision or no judgment in history
    """
    list_judgments_filtered = []
    list_history_decision = []
    if not os.path.exists(output_path_judgments_filtered) or not os.path.exists(output_path_judgments_decision_filter):

        list_judgments_filtered, list_history_decision = filter_decision(list_judgments_non_empty_history)

        write_output(list_judgments_filtered, output_path_judgments_filtered)
        write_output(list_history_decision, output_path_judgments_decision_filter)

    """
    step 3. linking the judgments between histories
    """
    list_judgments_filtered = reader_json(output_path_judgments_filtered)
    
    list_judgments_link = linking_history(list_judgments_filtered)

    write_output(list_judgments_link, output_path_judgments_link)

    """
    step 4. analyzing the linking results
    """
    list_link_wo_filter = reader_json(output_path_judgments_link)

    sorted_links_freq_overall, sorted_links_freq_detail = analysis(list_link_wo_filter, "frequency")
    sorted_links_length_overall, sorted_links_length_detail = analysis(list_link_wo_filter, "length")

    write_output([f"{link}: {count}" for link, count in sorted_links_freq_overall], output_path_analyze_freq)
    write_output([f"{link}: {count}" for link, count in sorted_links_length_overall], output_path_analyze_length)
    write_output([f"{link}: {count}" for link, count in sorted_links_freq_detail], output_path_analyze_freq_detail)
    write_output([f"{link}: {count}" for link, count in sorted_links_length_detail], output_path_analyze_length_detail)

    """
    step 5. filtering jid == null or secret case (but exception existing)
    """
    list_link_wo_filter = reader_json(output_path_judgments_link)

    list_link_filtered, list_link_useless = filter_useless_link(list_link_wo_filter)
    
    write_output(list_link_filtered, output_path_judgments_link_filtered)
    write_output(list_link_useless, output_path_judgments_link_useless)

    """
    step 6. analyzing the linking result with filtering useless judgments
    """
    list_link_filter = reader_json(output_path_judgments_link_filtered)

    sorted_links_freq_overall, sorted_links_freq_detail = analysis(list_link_filter, "frequency")
    sorted_links_length_overall, sorted_links_length_detail = analysis(list_link_filter, "length")

    write_output([f"{link}: {count}" for link, count in sorted_links_freq_overall], output_path_analyze_freq_filtered)
    write_output([f"{link}: {count}" for link, count in sorted_links_length_overall], output_path_analyze_length_filtered)
    write_output([f"{link}: {count}" for link, count in sorted_links_freq_detail], output_path_analyze_freq_detail_filtered)
    write_output([f"{link}: {count}" for link, count in sorted_links_length_detail], output_path_analyze_length_detail_filtered)

    """
    step 7. description size of each steps
    """
    print(f"Total unique judgments: {len(list_unique_judgments)}")
    print(f"Total judgments with non-empty history: {len(list_judgments_non_empty_history)}")
    print(f"Total judgments with empty history: {len(list_file_judgments_empty_history)}")
    print(f"Total judgments after filtering non-empty history: {len(list_judgments_filtered)}")
    print(f"Total judgments with decision history: {len(list_history_decision)}") # meaning how many judgments have filtered decision history
    print(f"Total judgments with link: {len(list_judgments_link)}")
    print(f"Total judgments with link after filtering useless judgments: {len(list_link_filtered)}")
    print(f"Total judgments with useless links: {len(list_link_useless)}")

    """
    result of step 7.
    Total unique judgments: 4137
    Total judgments with non-empty history: 3556
    Total judgments with empty history: 581
    Total judgments after filtering non-empty history: 3556
    Total judgments with decision history: 1863 > meaning 3,556 - 1,863 = 1,693 judgments have no decision history (excluding unknown jid and text)
    Total judgments with link: 3556
    Total judgments with link after filtering useless judgments: 2269
    Total judgments with useless links: 1287
    """

    ### for init test
    """
    output_path_all_links = './unique/retire/all_links.jsonl'
    output_path_missing_unknown = './unique/retire/missing_unknown.txt'
    output_path_missing_links = './unique/retire/missing_links.txt'
    list_all_links = []
    list_missing_links = []
    list_missing_judgment = []
    list_missing_no_judgment = []
    list_missing_unknown = []
    list_missing_invalid = []

    list_unique_judgments = reader_json(path_unique_judgments)

    for judgment in list_unique_judgments:
        jid = judgment['JID']
        histories = judgment['history']
        pointer_all_links = True
        for history in histories:
            link = history['link2json']
            text = history['text']
            if not link:
                pointer_all_links = False
                if "判決" in text:
                    list_missing_judgment.append(text)
                if "裁定" in text:
                    list_missing_no_judgment.append(text)
                if "判決" not in text and "裁定" not in text:
                    list_missing_unknown.append(text)
                if "判決" in text and "裁定" in text:
                    list_missing_invalid.append(text)
        if pointer_all_links:
            list_all_links.append(judgment)
        else:
            list_missing_links.append(jid)

    write_output(list_all_links, output_path_all_links)
    write_output(list_missing_unknown, output_path_missing_unknown)
    write_output(list_missing_links, output_path_missing_links)

    print(f"Total unique judgments: {len(list_unique_judgments)}")
    print(f"Total judgments with all links: {len(list_all_links)}")
    print(f"Total judgments with missing links: {len(list_missing_links)}")
    print(f"Total judgments with missing judgment: {len(list_missing_judgment)}")
    print(f"Total judgments with missing no judgment: {len(list_missing_no_judgment)}")
    print(f"Total judgments with missing unknown: {len(list_missing_unknown)}")
    print(f"Total judgments with missing invalid: {len(list_missing_invalid)}")
    print(f"missing links (judgment): {list_missing_judgment}")
    print(f"missing links (no judgment): {list_missing_no_judgment}")
    print(f"missing links (unknown): {list_missing_unknown[:5]}")
    """
    ### for init test

if __name__ == "__main__":
    link()