import os

def scan_directory(path):
    """
    Scans a directory and returns a tree structure.
    """
    root = {'name': os.path.basename(path), 'path': path, 'is_dir': True, 'children': []}
    try:
        for entry in os.scandir(path):
            if entry.name.startswith('.') or entry.name == '__pycache__':
                continue
            if entry.is_dir():
                root['children'].append(scan_directory(entry.path))
            else:
                root['children'].append({'name': entry.name, 'path': entry.path, 'is_dir': False})
    except OSError:
        return None
    return root

if __name__ == '__main__':
    import json
    import shutil

    # Create a dummy directory structure for testing
    if not os.path.exists('test_dir'):
        os.makedirs('test_dir/subdir')
        with open('test_dir/file1.txt', 'w') as f:
            f.write('hello')
        with open('test_dir/subdir/file2.txt', 'w') as f:
            f.write('world')

    tree = scan_directory('test_dir')
    print(json.dumps(tree, indent=4))

    # Clean up the dummy directory
    if os.path.exists('test_dir'):
        shutil.rmtree('test_dir')
