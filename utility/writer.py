import os
import json

def write_output(list_output: list, output_path: str):
    """
    write output to file
    """
    if not os.path.exists(output_path):
        with open(output_path, 'w', encoding = 'utf-8') as f:
            for item in list_output:
                if output_path.endswith('.jsonl'):
                    text = json.dumps(item, ensure_ascii = False)
                else:
                    text = item
                f.write(text + "\n")
    else:
        print(f"Output file {output_path} already exists. No changes made.")

def write_json(dict_content, output_path: str):
    output_diretory = os.path.dirname(output_path)
    if not os.path.exists(output_diretory):
        os.makedirs(output_diretory)
    if not os.path.exists(output_path):
        with open(output_path, 'w', encoding = 'utf-8') as f:
            json.dump(dict_content, f, indent = 4, ensure_ascii = False)
    else:
        print(f"JSON file {output_path} already exists. No changes made.")