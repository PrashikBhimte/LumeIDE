def tool_read_file(file_path: str):
    print(f"Reading file: {file_path}")
    try:
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        return str(e)

def tool_write_file(file_path: str, content: str):
    print(f"Writing to file: {file_path}")
    try:
        with open(file_path, "w") as f:
            f.write(content)
        return "File written successfully."
    except Exception as e:
        return str(e)
