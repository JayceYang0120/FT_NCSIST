import json

def reader_txt(file_path: str) -> list:
    """
    read a text file and return a list of lines.
    args:
        file_path: str, Path to the text file.
    returns:
        list_lines: list, List of lines in the file.
    """
    list_lines = []
    with open(file_path, 'r', encoding = 'utf-8') as f:
        for line in f:
            file_name = line.strip()
            jid = file_name if len(file_name.split(".")) == 1 else file_name.split(".")[0]
            list_lines.append(jid)
    return list_lines

def reader_json(file_path: str) -> list:
    """
    Reads a JSONL file and returns a list of dictionaries.
    args:
        file_path: str, path to the JSONL file.
    returns:
        data: list, a list of dictionaries parsed from the JSONL file.
    """
    data = None
    if file_path.endswith('.jsonl'):
        data = []
        with open(file_path, 'r', encoding = 'utf-8') as f:
            for line in f:
                data.append(json.loads(line.strip()))
    elif file_path.endswith('.json'):
        with open(file_path, 'r', encoding = 'utf-8') as f:
            data = json.load(f)
    return data