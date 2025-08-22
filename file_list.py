import os
import re
import json
import rarfile
from pathlib import Path

from utility import reader_json, write_output, write_json

from tqdm import tqdm

def _check_files(path: str) -> bool:
    """
    Check if the given directory contains any files.
    args:
        path: str, Path to the directory.
    returns:
        bool: True if the directory contains files, False otherwise.
    """
    return any(p.is_file() for p in Path(path).iterdir())

def crop_judgment(judgment: dict ) -> dict:
    """
    學長的code
    """
    # init
    result = dict()
    jfull_raw = judgment['JFULL'].splitlines()    
    result['案由'] = judgment['JTITLE']
    result['年份'] = judgment['JYEAR']
    result['字別'] = judgment['JCASE']

    # build patterns
    titles = ['主文', '事實', '理由', '事實及理由', '事實及理由要領']
    titles2 = ['相對人', '被告']
    pattern_title = '^\s*(' + '|'.join(['\s*'.join(title) for title in titles]) + ')\s*$'
    pattern_date = '^\s*中\s*華\s*民\s*國.*年.*月.*日\s*$'

    # divide section
    flag = None
    for num, line in enumerate(jfull_raw):
        if num == 0: # 標題=line1 e.g., 臺灣臺北地方法院民事簡易判決\u3000\u3000\u3000108年度北勞簡字第33號
            result['標題'] = []
            result['標題'].append(line)

        # section
        if re.match(pattern_title, line) is not None:
            flag = re.sub('\s', '', line)
            result[flag] = list()
        elif re.match(pattern_date, line) is not None:
            flag = None
            break
        elif flag is not None:
            result[flag].append(line.strip())        
    # 解決沒有主文或理由段落
    if len(result.keys()) < 3:
        flag = None
        for num, line in enumerate(jfull_raw):
            # sections
            if re.match('.\s+.\s+人|原\s+告|上列', line):
                if flag is None:
                    flag = '內文'
                    result[flag] = list()
                continue
            elif re.match(pattern_date, line) is not None:
                flag = None
                break
            elif flag is not None:
                result[flag].append(line)
    return result

def resplit_judgment_into_numbered_list(judgment: dict) -> dict:
    """
    學長的code
    """
    # init
    result = dict()
    r1  = ('①','②','③','④','⑤','⑥','⑦','⑧','⑨','⑩','⑪','⑫','⑬','⑭','⑮','⑯','⑰','⑱','⑲','⑳')
    r2  = ('⑴','⑵','⑶','⑷','⑸','⑹','⑺','⑻','⑼','⑽','⑾','⑿','⒀','⒁','⒂','⒃','⒄','⒅','⒆','⒇')
    r3  = ('Ⅰ','Ⅱ','Ⅲ','Ⅳ','Ⅴ','Ⅵ','Ⅶ','Ⅷ','Ⅸ','Ⅹ')
    r4  = ('壹、', '貳、', '參、', '叄、', '叁、', '参、', '肆、', '伍、', '陸、', '柒、', '捌、', '玖、', '拾、')
    r5  = ('㈠','㈡','㈢','㈣','㈤','㈥','㈦','㈧','㈨','㈩')
    r6  = ('㊀', '㊁', '㊂', '㊃', '㊄', '㊅', '㊆', '㊇', '㊈', '㊉')
    r7  = ('❶', '❷', '❸', '❹', '❺', '❻', '❼', '❽', '❾', '❿', '⓫', '⓬', '⓭', '⓮', '⓯', '⓰', '⓱', '⓲', '⓳', '⓴')
    r8  = ('⒈', '⒉', '⒊', '⒋', '⒌', '⒍', '⒎', '⒏', '⒐', '⒑', '⒒', '⒓', '⒔', '⒕', '⒖', '⒗', '⒘', '⒙', '⒚', '⒛')
    r9  = ('⓵', '⓶', '⓷', '⓸', '⓹', '⓺', '⓻', '⓼', '⓽', '⓾')
    r10 = ('（一）', '（二）', '（三）', '（四）', '（五）', '（六）', '（七）', '（八）', '（九）', '（十）', '（十一）', '（十二）', '（十三）', '（十四）', '（十五）', '（十六）', '（十七）', '（十八）', '（十九）', '（二十）')
    r11 = ('(一)', '(二)', '(三)', '(四)', '(五)', '(六)', '(七)', '(八)', '(九)', '(十)', '(十一)', '(十二)', '(十三)', '(十四)', '(十五)', '(十六)', '(十七)', '(十八)', '(十九)', '(二十)')
    r12 = ('一、', '二、', '三、', '四、', '五、', '六、', '七、', '八、', '九、', '十、', '十一、', '十二、', '十三、', '十四、', '十五、', '十六、', '十七、', '十八、', '十九、', '二十 ')
    r13 = ('A.', 'B.', 'C.', 'D.', 'E.', 'F.', 'G.', 'H.', 'I.', 'J.', 'K.')
    r14 = ('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.', '11.', '12.', '13.', '14.', '15.', '16.', '17.', '18.', '19.', '20.')
    r15 = ('甲、', '乙、', '丙、', '丁、', '戊、', '己、', '庚、', '辛、', '壬、', '奎、')

    segment_list = [r15, r4, r12, r11, r10, r5, r14, r13, r6, r1, r2, r7, r8, r9, r3]
    all_segment = r15 + r4 + r12 + r11 + r10 + r5 + r14 + r13 + r6 + r1 + r2 + r7 + r8 + r9 + r3

    titles = ['標題', '年份', '案由', '字別']
    # resplit
    for title, text in judgment.items():
        # 標題、案由
        if title in titles:
            merge = ''.join([re.sub('\s', '', line) for line in text])
            result[title] = merge
        else:
            tmp = ''
            count_segment = 1
            main_segment_title = []
            result[title] = {str(1): []}

            for line in text:
                l = re.sub('\s', '', line)
                # 找到大標題
                if not main_segment_title:
                    for r in segment_list:
                        if l.startswith(r):
                            main_segment_title = r
                            tmp += l
                            break
                    else:
                        tmp += l

                # 已有大類標題
                else:
                    # pop temp to result
                    if l.startswith(main_segment_title):
                        result[title][str(count_segment)].append(tmp)
                        count_segment += 1
                        result[title][str(count_segment)] = []
                        tmp = l
                        # sub_segment = [temp]

                    elif l.startswith(all_segment):
                        result[title][str(count_segment)].append(tmp)
                        tmp = l
                    # push into temp
                    else:
                        tmp += l
            result[title][str(count_segment)].append(tmp)    
    return result

def find_notation(len_search, sentence_first):
    """
    想法: 找到input和global list_notation_all中r1 ~ r15的mapping符號，接著找到下一個符號
        e.g., 找到r11 = ['(一)', '(二)', '(三)', '(四)', '(五)']中的'(一)'後回傳'(一)'和'(二)'
    args:
        sentence_first: string, 第一個句子，原告主張、被告則以...的開頭句子
    return:
        notation_first: string, 第一個句子的notation
        notation_next: string, 第一個句子後面的下一個notation
    """
    pointer = False
    len_head = len_search if len(sentence_first) > len_search else len(sentence_first)
    sentence_head = sentence_first[:len_head]
    notation_first = None
    notation_next = None
    for i in range(len(list_notation_all)):
        if pointer:
            break
        for j, notation in enumerate(list_notation_all[i]):
            if notation in sentence_head:
                pointer = True
                notation_first = notation
                notation_next = list_notation_all[i][j + 1] if j + 1 < len(list_notation_all[i]) else None
                break
    if not pointer:
        return None, None
    return notation_first, notation_next

def find_next_sentence(notation_next, sentence):
    len_head = 50 if len(sentence) > 50 else len(sentence)
    if notation_next != "參":
        return notation_next in sentence[:len_head] if notation_next else False
    ### in case of "參" is used as notation
    list_third = ['參、', '参、', '叁、', '叄、']
    for notation in list_third:
        if notation in sentence[:len_head]:
            return True
    return False
    ### in case of "參" is used as notation

def find_sentences(pattern: str, list_text: list) -> tuple:
    temp_list = []
    pointer = False
    pointer_notation = True
    notation_first = None
    notation_next = None
    len_search = 10
    for sentence in list_text:
        if not pointer:
            if pattern.search(sentence):
                pointer = True
                temp_list.append(sentence)
                notation_first, notation_next = find_notation(len_search, sentence)
                if notation_first is None or notation_next is None:
                    len_search = 50 # 2nd search
                    notation_first, notation_next = find_notation(len_search, sentence)
                    if notation_first is None or notation_next is None:
                        pointer_notation = False
                        return temp_list, pointer_notation
        else:
            if find_next_sentence(notation_next, sentence):
                break
            temp_list.append(sentence)
    return temp_list, pointer_notation

def split_defense(text: str, JID: str) -> tuple:
    """
    邏輯
    step1: init temp_list and pointer
    step2: iterate through list_all to find pattern, then set pointer to True
    step3: append sentences to temp_list until find next notation
    """

    pattern_plaintiff = re.compile(r"(?:^|[、])\s*((?:本件)?(?:原告|被上訴人|上訴人)(?:等)?(?:起訴)?(?:主張|聲明|方面))")
    pattern_defendant = re.compile(r"(?:^|[、])\s*(((?:被告)(?:等)?(?:主張|部分|則以|聲明|答辯|抗辯|辯以|辯稱|方面))|(?:被上訴人|上訴人)(?:等)?(?:則以|答辯|抗辯|辯以)|(?:被上訴人)(?:等)?(?:方面))")
    pattern_noArgument = re.compile(r"不爭執(?:之)?(?:事項|事實|要旨|處)")
    pattern_argument = re.compile(r"(?<!不)爭執(?:之)?(?:事項|事實|要旨|處)|^(?!.*不爭執(?:之)?事項).*爭點")
    pattern_reason = re.compile(r"(得心證(?:之|的)?理由|(?:法院|本院)(?:之|的)?(?:判斷|論斷|認定)|(?:茲)?分述(?:如下|之)?)")

    ### patterns of 2nd search
    pattern_plaintiff_2 = re.compile(r"(?:^|[、])\s*((?:[\u4e00-\u9fa5○（）()、，0-9０-９]{1,50})(?:起訴)?(?:主張|聲明)(?:略以)?[：:])")
    pattern_defendant_2 = re.compile(r"(?:^|[、])\s*(((?:被告)(?:等)?(?:主張|部分|則以|聲明|答辯|抗辯|辯以|辯稱))|(?:[\u4e00-\u9fa5○（）()、，0-9０-９]{1,50})(?:則以|答辯|抗辯|辯以|辯稱)(?:略以)?[：:])")
    pattern_reason_2 = re.compile(r"(?:經查)[：:]")
    ### patterns of 2nd search

    ### patterns of 被告未於言詞辯論期日到場
    pattern_defendant_waiver = re.compile(r"(?:被告)?未於言詞辯論期日到場")
    ### patterns of 被告未於言詞辯論期日到場

    ### patterns of 原告、被告方面 + 沒有項目編號 - deprecated
    pattern_plaintiff_no_number = re.compile(r"(?:原告|上訴人)(?:等)?(?:起訴)?(?:主張|聲明|方面)[：:]")
    ### patterns of 原告、被告方面 + 沒有項目編號 - deprecated

    titles_prior = {'事實', '理由', '事實及理由', '事實及理由要領'} # care '主文'造成的key值混淆
    titles_candidate = {'主文'}

    dict_log_title = dict() # storing log with judgment mapping "主文"
    dict_log_notation = dict() # storing log with judgment having undefined notation
    dict_log_2nd = dict() # storing log with judgment having 2nd search
    dict_log_waiver = dict() # storing log with 被告未於言詞辯論期日到場

    pointer_notation = False
    pointer_2key = False

    match_key = None
    match_key_reason = None # for older judgment which has "事實" and "理由" as keys

    match_title = titles_prior & text.keys()
    if len(match_title) > 2:
        dict_log_title = {JID: "有多個事實或理由"}
        return text, dict_log_title, dict_log_notation, dict_log_2nd, dict_log_waiver
    if "事實" in match_title and "理由" in match_title:
        pointer_2key = True
        match_key = "事實"
        match_key_reason = "理由"
        pattern_plaintiff = re.compile(r"(?:^|[、])\s*((?:原告|上訴人)(?:等)?(?:起訴)?(?:方面|主張|聲明))")
        pattern_defendant = re.compile(r"(?:^|[、])\s*(((?:被告)(?:等)?(?:方面|主張|部分|則以|聲明|答辯|抗辯|辯以|辯稱))|(?:被上訴人)(?:等)?(?:方面|則以|答辯|抗辯|辯以))")
        pattern_plaintiff_2 = re.compile(r"(?:^|[、])\s*((?:[\u4e00-\u9fa5○（）()、，0-9０-９]{1,50})(?:起訴)?(?:方面|主張|聲明)[：:])")
        pattern_defendant_2 = re.compile(r"(?:^|[、])\s*((?:[\u4e00-\u9fa5○（）()、，0-9０-９]{1,50})(?:則以|答辯|抗辯|辯以|辯稱)[：:])")
    elif match_title:
        match_key = match_title.pop()
    else:
        match_title = titles_candidate & text.keys()
        if match_title:
            match_key = match_title.pop()
            dict_log_title = {JID: "無事實或理由，從主文get"}
        else:
            dict_log_title = {JID: "無事實或理由及主文"}
            return text, dict_log_title, dict_log_notation, dict_log_2nd, dict_log_waiver
    ### avoid to non order in dictionary
    keys = [key for key in text[match_key].keys()]
    keys.sort()
    list_all = []
    for i in range(len(keys)):
        list_all.extend(text[match_key][str(keys[i])])

    # list_all_reason for older judgment which has "事實" and "理由" as keys
    if match_key_reason:
        keys = [key for key in text[match_key_reason].keys()]
        keys.sort()
        list_all_reason = []
        for i in range(len(keys)):
            list_all_reason.extend(text[match_key_reason][str(keys[i])])
    ### avoid to non order in dictionary

    temp_dict = dict()

    ### extract the 原告主張
    # key_list[0] should be "原告主張"
    temp_dict[key_list[0]], pointer = find_sentences(pattern_plaintiff, list_all)
    if not pointer and not pointer_notation:
        pointer_notation = True
        dict_log_notation[JID] = "notation"
    if not temp_dict[key_list[0]] and pointer: # 2nd search
        temp_dict[key_list[0]], pointer = find_sentences(pattern_plaintiff_2, list_all)
        dict_log_2nd[JID] = [key_list[0]]
    ### extract the 原告主張

    ### extract the 被告則以
    # key_list[1] should be "被告則以"
    temp_dict[key_list[1]], pointer = find_sentences(pattern_defendant, list_all)
    if not pointer and not pointer_notation:
        pointer_notation = True
        dict_log_notation[JID] = "notation"
    if not temp_dict[key_list[1]] and pointer: # 2nd search
        temp_dict[key_list[1]], pointer = find_sentences(pattern_defendant_2, list_all)
        if dict_log_2nd:
            dict_log_2nd[JID].append(key_list[1])
        else:
            dict_log_2nd[JID] = [key_list[1]]
    if not temp_dict[key_list[1]] and pointer: # if still not found, try capturing pattern "被告未於言詞辯論期日到場"
        finding, pointer = find_sentences(pattern_defendant_waiver, list_all)
        if pointer and finding:
            temp_dict[key_list[1]] = ["被告未於言詞辯論期日到場"]
            dict_log_waiver[JID] = "未於言詞辯論期日到場"
    ### extract the 被告則以

    ### extract the 不爭執事項
    # key_list[2] should be "不爭執事項" or "不爭議事項"
    temp_dict[key_list[2]], pointer = find_sentences(pattern_noArgument, list_all)
    if not pointer and not pointer_notation:
        pointer_notation = True
        dict_log_notation[JID] = "notation"
    ### extract the 不爭執事項

    ### extract the 本院心證
    # key_list[3] should be "本院心證" or "法院心證"
    temp_dict[key_list[3]], pointer = find_sentences(pattern_reason, list_all)
    if not pointer and not pointer_notation:
        pointer_notation = True
        dict_log_notation[JID] = "otation"
    if not temp_dict[key_list[3]] and pointer and match_key_reason: # for older judgment
        temp_dict[key_list[3]], pointer = find_sentences(pattern_reason, list_all_reason)
        if not temp_dict[key_list[3]] and pointer: # if still not found, try using all text "理由" - 2nd search
            temp_dict[key_list[3]] = list_all_reason
            if dict_log_2nd:
                dict_log_2nd[JID].append(key_list[3])
            else:
                dict_log_2nd[JID] = [key_list[3]]
    ### extract the 本院心證

    ### extract the 爭執事項
    # key_list[4] should be "爭執事項" or "爭議事項"
    temp_dict[key_list[4]], pointer = find_sentences(pattern_argument, list_all)
    if not pointer and not pointer_notation:
        pointer_notation = True
        dict_log_notation[JID] = "notation"
    ### extract the 爭執事項

    ### extract the 本院心證 - 2nd search
    # 由於以些判決法院心證和爭執事項會放一起，所以法院心證 - 2nd search的時間點放在爭執事項之後
    if not temp_dict[key_list[3]] and not temp_dict[key_list[4]] and not dict_log_notation:
        temp_dict[key_list[3]], _ = find_sentences(pattern_reason_2, list_all) # 不會有list_all_reason的情況
    ### extract the 本院心證 - 2nd search

    # notice diff
    # text[match_key] = temp_dict
    if match_key != '主文' and not pointer_2key:
        text.pop(match_key, None)
    if pointer_2key:
        text.pop('事實', None)
        text.pop('理由', None)
    text["事實及理由"] = temp_dict
    return text, dict_log_title, dict_log_notation, dict_log_2nd, dict_log_waiver

def check(judgment: str) -> tuple:
    """
    check if the judgment has the keys '案由', '年份', '字別', '標題', '主文', '事實及理由': {'原告主張', '被告則以', '本院心證'}, '檔案名稱'
    """
    dic_all = dict()
    dic_fact = dict()
    match_title = {'事實及理由'} & judgment.keys()
    if match_title:
        match_key = match_title.pop()
    else:
        match_title = {'主文'} & judgment.keys()
        if match_title:
            match_key = match_title.pop()
        else:
            dic_all[judgment['檔案名稱']] = ['主文', '事實及理由']
            dic_fact[judgment['檔案名稱']] = ['all keys are empty']
            return dic_all, dic_fact

    keys_all = ['案由', '年份', '字別', '標題', '主文', match_key, '檔案名稱']
    keys_fact = [key_list[0], key_list[1], key_list[3], key_list[4]]
    empty_keys_all = [key for key in keys_all if key in judgment.keys() and len(judgment[key]) == 0]
    empty_keys_fact = [key for key in keys_fact if key in judgment[match_key] and (len(judgment[match_key][key]) == 0)]
    
    if empty_keys_all:
        dic_all[judgment['檔案名稱']] = empty_keys_all
    if keys_fact[0] in empty_keys_fact or keys_fact[1] in empty_keys_fact or (keys_fact[2] in empty_keys_fact and keys_fact[3] in empty_keys_fact):
        dic_fact[judgment['檔案名稱']] = empty_keys_fact
    return dic_all, dic_fact

def check_log(log: dict, list_log: list) -> list:
    if log:
        list_log.append(log)
    return list_log

def file_list():
    ### parameters for links path
    path_jsonl_file = "./links/link_filtered.jsonl" 
    ### parameters for links path

    ### parameters for step 1.
    output_path_list_files = "./lists/file_list.txt"
    output_path_list_files_first_case = "./lists/cases_first.txt"
    output_path_list_files_appeal_case = "./lists/cases_appeal.txt"
    output_path_list_cases_wo_jid = "./lists/cases_wo_jid.txt"
    ### parameters for step 1.

    ### parameters for step 2.
    path_dir_dataset = "../Dataset/"
    output_path_dir_original = "./assets/"
    ### parameters for step 2.

    ### parameters for step 3.
    path_dir_json_original = output_path_dir_original
    output_path_dir_extracted = "./dataset/"
    output_path_log_all = './logs/extraction/log_all.jsonl'
    output_path_log_fact = './logs/extraction/log_fact.jsonl'
    output_path_log_title = './logs/extraction/log_title.jsonl'
    output_path_log_notation = './logs/extraction/log_notation.jsonl'
    output_path_log_2nd = './logs/extraction/log_2nd.jsonl'
    output_path_log_waiver = './logs/extraction/log_waiver.jsonl'
    ### parameters for step 3.

    ### parameters for step 4.
    path_dir_json_extracted = output_path_dir_extracted
    output_path_missing_files = './logs/missing/missing_files.jsonl'
    ### parameters for step 4.

    ### variables for notations
    r1  = ['①','②','③','④','⑤','⑥','⑦','⑧','⑨','⑩','⑪','⑫','⑬','⑭','⑮','⑯','⑰','⑱','⑲','⑳']
    r2  = ['⑴','⑵','⑶','⑷','⑸','⑹','⑺','⑻','⑼','⑽','⑾','⑿','⒀','⒁','⒂','⒃','⒄','⒅','⒆','⒇']
    r3  = ['Ⅰ','Ⅱ','Ⅲ','Ⅳ','Ⅴ','Ⅵ','Ⅶ','Ⅷ','Ⅸ','Ⅹ']
    r4  = ['壹、', '貳、', '參、', '叄、', '叁、', '参、', '肆、', '伍、', '陸、', '柒、', '捌、', '玖、', '拾、']
    r5  = ['㈠','㈡','㈢','㈣','㈤','㈥','㈦','㈧','㈨','㈩']
    r6  = ['㊀', '㊁', '㊂', '㊃', '㊄', '㊅', '㊆', '㊇', '㊈', '㊉']
    r7  = ['❶', '❷', '❸', '❹', '❺', '❻', '❼', '❽', '❾', '❿', '⓫', '⓬', '⓭', '⓮', '⓯', '⓰', '⓱', '⓲', '⓳', '⓴']
    r8  = ['⒈', '⒉', '⒊', '⒋', '⒌', '⒍', '⒎', '⒏', '⒐', '⒑', '⒒', '⒓', '⒔', '⒕', '⒖', '⒗', '⒘', '⒙', '⒚', '⒛']
    r9  = ['⓵', '⓶', '⓷', '⓸', '⓹', '⓺', '⓻', '⓼', '⓽', '⓾']
    r10 = ['（一）', '（二）', '（三）', '（四）', '（五）', '（六）', '（七）', '（八）', '（九）', '（十）', '（十一）', '（十二）', '（十三）', '（十四）', '（十五）', '（十六）', '（十七）', '（十八）', '（十九）', '（二十）']
    r11 = ['(一)', '(二)', '(三)', '(四)', '(五)', '(六)', '(七)', '(八)', '(九)', '(十)', '(十一)', '(十二)', '(十三)', '(十四)', '(十五)', '(十六)', '(十七)', '(十八)', '(十九)', '(二十)']
    r12 = ['一、', '二、', '三、', '四、', '五、', '六、', '七、', '八、', '九、', '十、', '十一、', '十二、', '十三、', '十四、', '十五、', '十六、', '十七、', '十八、', '十九、', '二十 ']
    r13 = ['A.', 'B.', 'C.', 'D.', 'E.', 'F.', 'G.', 'H.', 'I.', 'J.', 'K.']
    r14 = ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.', '11.', '12.', '13.', '14.', '15.', '16.', '17.', '18.', '19.', '20.']
    r15 = ['甲、', '乙、', '丙、', '丁、', '戊、', '己、', '庚、', '辛、', '壬、', '奎、']
    ### variables for notations

    ### variables for keys
    global key_list
    key_list = ["原告主張", "被告則以", "不爭議項", "法院心證", "爭議事項"]
    ### variables for keys

    """
    step 1. create a list of jid with first cases > size = 2269
    """
    list_file_list = []
    list_file_first_case = []
    list_file_appeal_case = []
    list_file_wo_jid = []
    list_links = reader_json(path_jsonl_file)
    for item in list_links:
        histories = item["history"]
        for index, history in enumerate(histories):
            jid = history["link2json"]
            int_case = history["int_case"]
            if int_case != 0:
                list_file_wo_jid.append(history["text"])
                continue
            list_file_list.append(jid)
            if index == 0:
                list_file_first_case.append(jid)
            else:
                list_file_appeal_case.append(jid)
    write_output(list_file_list, output_path_list_files)
    write_output(list_file_first_case, output_path_list_files_first_case)
    write_output(list_file_appeal_case, output_path_list_files_appeal_case)
    write_output(list_file_wo_jid, output_path_list_cases_wo_jid)

    """
    step 2. create json files about original version
    """
    list_original_files = []
    if not _check_files(output_path_dir_original):
        for doc in tqdm(os.listdir(path_dir_dataset), desc = "Processing RAR files"):
            file_path = os.path.join(path_dir_dataset, doc)
            with rarfile.RarFile(file_path) as rf:
                for fileinfo in rf.infolist():
                    file_name = fileinfo.filename
                    JID = file_name.split("/")[-1].split(".")[0]
                    if JID in list_file_list:
                        with rf.open(file_name) as jf:
                            json_data = json.load(jf)
                            list_original_files.append(json_data)
    for item in list_original_files:
        jid = item["JID"]
        output_path_json = os.path.join(output_path_dir_original, f"{jid}.json")
        write_json(item, output_path_json)

    """
    step 3. create json files about processed version
    """
    list_extracted_files = []
    list_log_all = []
    list_log_fact = []
    list_log_title = []
    list_log_notation = []
    list_log_2nd = []
    list_log_waiver = []
    global list_notation_all
    list_notation_all = [r15, r4, r12, r11, r10, r5, r14, r13, r6, r1, r2, r7, r8, r9, r3]

    if not _check_files(output_path_dir_extracted):
        for doc in tqdm(os.listdir(path_dir_json_original), desc = "Processing JSON files"):
            file_path = os.path.join(path_dir_json_original, doc)
            data = reader_json(file_path)
            jid = data['JID']
            dict_judgment = crop_judgment(data)
            judgment_string = resplit_judgment_into_numbered_list(dict_judgment)
            judgment, dict_log_title, dict_log_notation, dict_log_2nd, dict_log_waiver = split_defense(judgment_string, data['JID'])
            judgment['檔案名稱'] = jid + '.json'
            dict_log_all, dict_log_fact = check(judgment)
            list_log_all = check_log(dict_log_all, list_log_all)
            list_log_fact = check_log(dict_log_fact, list_log_fact)
            list_log_title = check_log(dict_log_title, list_log_title)
            list_log_notation = check_log(dict_log_notation, list_log_notation)
            list_log_2nd = check_log(dict_log_2nd, list_log_2nd)
            list_log_waiver = check_log(dict_log_waiver, list_log_waiver)
            output_path_judgment = os.path.join(output_path_dir_extracted, judgment['檔案名稱'])
            write_json(judgment, output_path_judgment)
        write_output(list_log_all, output_path_log_all)
        write_output(list_log_fact, output_path_log_fact)
        write_output(list_log_title, output_path_log_title)
        write_output(list_log_notation, output_path_log_notation)
        write_output(list_log_2nd, output_path_log_2nd)
        write_output(list_log_waiver, output_path_log_waiver)
    
    """
    step 4. check the files isn't get in dataset
    """
    list_existed = []
    for file in os.listdir(path_dir_json_extracted):
        jid = file.split(".")[0]
        list_existed.append(jid)
    diff = list(set(list_file_list) - set(list_existed))
    write_output(diff, output_path_missing_files)

if __name__ == "__main__":
    file_list()