import os

from tqdm import tqdm

from utility import reader_json, write_output

def analyze():
    """
    description:
        Analyze the original dataset in "./assets/", find difference between retire and retire + base
    """

    ### parameters
    path_dir_dataset = "./assets/"
    output_path_list_files_retire = "./lists/analysis/retire/file_list.txt"
    output_path_list_files_wo_retire = "./lists/analysis/retire/file_list_wo_retire.txt"
    output_path_list_files_basis = "./lists/analysis/basis/file_list.txt"
    output_path_list_files_wo_basis = "./lists/analysis/basis/file_list_wo_basis.txt"
    ### parameters

    ### variables for basis
    key_word_basis = "基數"
    key_word_retire = "退休"
    ### variables for basis

    list_files_list_retire = []
    list_files_list_wo_retire = []
    list_files_list_basis = []
    list_files_list_wo_basis = []

    for doc in tqdm(os.listdir(path_dir_dataset), desc = "Processing orginal dataset with key word"): # care 2 cases without 2000~2025
        file_path = os.path.join(path_dir_dataset, doc)
        data = reader_json(file_path)
        text_raw_jfull = data["JFULL"]
        jid = data["JID"]
        if key_word_retire in text_raw_jfull:
            list_files_list_retire.append(jid)
        else:
            list_files_list_wo_retire.append(jid)
        if key_word_basis in text_raw_jfull:
            list_files_list_basis.append(jid)
        else:
            list_files_list_wo_basis.append(jid)
    write_output(list_files_list_retire, output_path_list_files_retire)
    write_output(list_files_list_wo_retire, output_path_list_files_wo_retire)
    write_output(list_files_list_basis, output_path_list_files_basis)
    write_output(list_files_list_wo_basis, output_path_list_files_wo_basis)

if __name__ == "__main__":
    analyze()