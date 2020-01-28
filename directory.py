import os

# Test file for performing directory and file operations.

def check_names(path):
    if not os.path.exists(os.path.dirname(path)):
        print(f'File: {path}')
    else:
        print(f'Directory: {path}')

def is_path_directory(path):
    return os.path.isdir(os.path.dirname(path)) and not os.path.isfile(path)

check_names('/etc')
check_names('~/.bash_profile')
check_names('/')

print(is_path_directory('/etc'))
print(is_path_directory('~/.bash_profile'))
print(is_path_directory('/'))
print(is_path_directory('/etc/passwd'))

print(os.path.exists('/etc'))
print(os.path.exists('~/.bash_profile'))
print(os.path.exists('/'))
print(os.path.exists('/etc/passwd'))