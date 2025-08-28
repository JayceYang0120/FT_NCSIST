import os

from utility import reader_json, write_output

def unique():

    """
    description:
    1. filtering out cases with specific statutory provisions
    2. removing duplicates based on history content and finding out duplicate JID without version
    3. size of data description
    """

    ### parameters for step 1.
    path_history_all = './appeal/all_history.jsonl'
    specific_statutory_provisions = {
        "勞動基準法": ["55", "84.2"],
        "勞動基準法施行細則": ["5"]
    }
    output_path_filtered = f'./unique/filtered_history.jsonl'
    output_path_files_flitered = f'./logs/unique/history_filtered.txt'
    output_path_wo_relevant = f'./logs/unique/history_wo_relevant.txt'
    ### parameters for step 1.

    ### parameters for step 2.
    output_path_unique = f'./unique/unique_history.jsonl'
    output_path_unique_file = f'./logs/unique/unique_history.txt'
    output_path_duplicate_file = f'./logs/unique/duplicate_JID.txt'
    ### parameters for step 2.

    """
    step 1. filtering out cases with specific statutory provisions
    """
    list_history_keep = []
    list_JID_keep = []
    list_history_filtered = []
    list_files_filtered = []
    list_files_wo_relevant = []

    list_history_all = reader_json(path_history_all)

    for judgment in list_history_all:
        JID = judgment["JID"]
        related_law = judgment["related_law"]
        history = judgment["history"]
        pointer_relevant = False
        for law in related_law:
            law_name = law["law_name"]
            law_no = law["law_no"].split("、")
            if pointer_relevant:
                break
            if law_name in specific_statutory_provisions.keys():
                list_no_specific = specific_statutory_provisions[law_name]
                for no_specific in list_no_specific:
                    if no_specific in law_no:
                        pointer_relevant = True
                        break
        if pointer_relevant:
            if history and history not in list_history_keep:
                list_history_keep.append(history)
            if not history:
                list_JID_keep.append(JID)
    
    for judgment in list_history_all:
        JID = judgment["JID"]
        history = judgment["history"]
        if not history:
            if JID in list_JID_keep:
                list_files_filtered.append(JID)
                list_history_filtered.append(judgment)
            else:
                list_files_wo_relevant.append(JID)
        else:
            if history in list_history_keep:
                list_files_filtered.append(JID)
                list_history_filtered.append(judgment)
            else:
                list_files_wo_relevant.append(JID)
    write_output(list_history_filtered, output_path_filtered)
    write_output(list_files_filtered, output_path_files_flitered)
    write_output(list_files_wo_relevant, output_path_wo_relevant)

    """
    step 2. removing duplicates
    """
    list_unique_output = []
    list_unique_history = []
    list_unique_JID = []
    list_unique_JID_wo_version = []
    list_duplicate_JID_wo_version = []
    list_duplicate_JID = []

    list_history_filtered = reader_json(output_path_filtered)

    for instance_json in list_history_all:
        JID = instance_json["JID"]
        history = instance_json["history"]
        related_law = instance_json["related_law"]
        JID_wo_version = ",".join(JID.split(",")[:5])
        if not history:
            list_unique_JID.append(JID)
            list_unique_output.append({
                "JID": JID,
                "history": history,
                "related_law": related_law
            })
        else:        
            if history not in list_unique_history:
                list_unique_history.append(history)
                list_unique_JID.append(JID)
                list_unique_output.append({
                    "JID": JID,
                    "history": history,
                    "related_law": related_law
                })

        if JID_wo_version not in list_unique_JID_wo_version:
            list_unique_JID_wo_version.append(JID_wo_version)
        else:
            list_duplicate_JID_wo_version.append(JID_wo_version)

    for instance_json in list_history_filtered:
        JID = instance_json["JID"]
        JID_wo_version = ",".join(JID.split(",")[:5])
        if JID_wo_version in list_duplicate_JID_wo_version:
            list_duplicate_JID.append(JID)
    write_output(list_unique_output, output_path_unique)
    write_output(list_unique_JID, output_path_unique_file)
    write_output(list_duplicate_JID, output_path_duplicate_file)

    """
    step 3. dataset size description
    """
    print(f"Total cases processed: {len(list_history_all)}")
    print(f"Total unique cases after filtering out specific statutory provisions: {len(list_history_filtered)}")
    print(f"Total unique cases after deduplication of history: {len(list_unique_output)}")
    print(f"Total duplicate cases having same JID without version: {len(list_duplicate_JID)}")

if __name__ == "__main__":
    unique()