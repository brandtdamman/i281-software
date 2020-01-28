import os

# directory checker (determines if path given is dir or file)
# Cannot use ~ 'tilde' for singular use.  Must use FQFsN.

def check_names(path):
    if not os.path.exists(os.path.dirname(path)):
        print(f'File: {path}')
    else:
        print(f'Directory: {path}')

check_names('/etc')
check_names('~/.bash_profile')
check_names('/')
