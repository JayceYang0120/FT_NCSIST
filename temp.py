import os
import json
import shutil

from utility import reader_txt, write_output, write_json

import rarfile
from tqdm import tqdm

def temp():

    path_threshold = './temp/file_99.txt'
    path_list_files_filtered = './logs/unique/history_filtered.txt'
    path_files_duplicate_JID_wo_version = './logs/unique/duplicate_JID.txt'
    path_files_wo_retire = './temp/file_list_wo_retire.txt'
    path_files_wo_basis = './temp/file_list_wo_basis.txt'
    output_path_diff = './temp/intersection_wo_duplicate.txt'

    list_threshold = reader_txt(path_threshold)
    list_files_filtered = reader_txt(path_list_files_filtered)
    list_files_duplicate = reader_txt(path_files_duplicate_JID_wo_version)
    list_files_wo_retire = reader_txt(path_files_wo_retire)
    list_files_wo_basis = reader_txt(path_files_wo_basis)
    
    intersection = set(list_threshold).intersection(set(list_files_filtered))
    diff = intersection.difference(set(list_files_duplicate))
    diff_2 = diff.difference(set(list_files_wo_retire))
    diff_3 = diff_2.difference(set(list_files_wo_basis))
    list_diff = list(diff_3)
    
    write_output(list_diff, output_path_diff)

    print(f"len intersection: {len(intersection)}")
    print(f"len diff: {len(diff)}")
    print(f"len diff_2: {len(diff_2)}")
    print(f"len diff_3: {len(list_diff)}")

    path_dir_dataset = "../Dataset/"
    path_dir_LCS = './temp/dataset_LCS/'
    output_dir_original = './temp/dataset_original/'
    output_dir_result = './temp/dataset_result/'

    list_original_files = []
    for doc in tqdm(os.listdir(path_dir_dataset), desc = "Processing RAR files"):
        file_path = os.path.join(path_dir_dataset, doc)
        with rarfile.RarFile(file_path) as rf:
            for fileinfo in rf.infolist():
                file_name = fileinfo.filename
                JID = file_name.split("/")[-1].split(".")[0]
                if JID in list_diff:
                    with rf.open(file_name) as jf:
                        json_data = json.load(jf)
                        list_original_files.append(json_data)
    for item in list_original_files:
        JID = item["JID"]
        output_path_json = os.path.join(output_dir_original, f"{JID}.json")
        write_json(item, output_path_json)
    
    for file in os.listdir(path_dir_LCS):
        file_path = os.path.join(path_dir_LCS, file)
        JID = file.split(".")[0]
        if JID in list_diff:
            output_file = os.path.join(output_dir_result, file)
            if not os.path.exists(output_file):
                shutil.copy(file_path, output_file)

if __name__ == "__main__":
    temp()