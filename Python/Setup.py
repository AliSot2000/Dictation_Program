import os
import shutil

# File_Tree:
# /Diktierprogramm
#       /Python
#           Setup.py
#           Diktierprogramm.py
#           Request_Script.py
#           /_temp_txt
#               /_debug
#                   nr.json
#                   ...
#               nr.json
#               ...
#           /_temp_wav
#               /_debug
#                   /nr_debug
#                       nr.wav
#                       nr.txt
#               /nr
#                   nr.wav
#                   nr.txt
#               ...
#       /bash
#           /start_request
#       /venv
#           /bin
#               activate
#               ...
# add functionality to make python scripts

def overwrite_activate():
    script = '''# This file must be used with "source bin/activate" *from bash*
# you cannot run it directly

deactivate () {
    # reset old environment variables
    if [ -n "${_OLD_VIRTUAL_PATH:-}" ] ; then
        PATH="${_OLD_VIRTUAL_PATH:-}"
        export PATH
        unset _OLD_VIRTUAL_PATH
    fi
    if [ -n "${_OLD_VIRTUAL_PYTHONHOME:-}" ] ; then
        PYTHONHOME="${_OLD_VIRTUAL_PYTHONHOME:-}"
        export PYTHONHOME
        unset _OLD_VIRTUAL_PYTHONHOME
    fi

    # This should detect bash and zsh, which have a hash command that must
    # be called to get it to forget past commands.  Without forgetting
    # past commands the $PATH changes we made may not be respected
    if [ -n "${BASH:-}" -o -n "${ZSH_VERSION:-}" ] ; then
        hash -r
    fi

    if [ -n "${_OLD_VIRTUAL_PS1:-}" ] ; then
        PS1="${_OLD_VIRTUAL_PS1:-}"
        export PS1
        unset _OLD_VIRTUAL_PS1
    fi

    unset VIRTUAL_ENV
    if [ ! "${1:-}" = "nondestructive" ] ; then
    # Self destruct!
        unset -f deactivate
    fi
}

# unset irrelevant variables
deactivate nondestructive
'''
    script += f'VIRTUAL_ENV="{venv_location}"\n'
    script += '''export VIRTUAL_ENV

_OLD_VIRTUAL_PATH="$PATH"
PATH="$VIRTUAL_ENV/bin:$PATH"
export PATH

# unset PYTHONHOME if set
# this will fail if PYTHONHOME is set to the empty string (which is bad anyway)
# could use `if (set -u; : $PYTHONHOME) ;` in bash
if [ -n "${PYTHONHOME:-}" ] ; then
    _OLD_VIRTUAL_PYTHONHOME="${PYTHONHOME:-}"
    unset PYTHONHOME
fi

if [ -z "${VIRTUAL_ENV_DISABLE_PROMPT:-}" ] ; then
    _OLD_VIRTUAL_PS1="${PS1:-}"
    if [ "x(venv) " != x ] ; then
	PS1="(venv) ${PS1:-}"
    else
    if [ "`basename \"$VIRTUAL_ENV\"`" = "__" ] ; then
        # special case for Aspen magic directories
        # see http://www.zetadev.com/software/aspen/
        PS1="[`basename \`dirname \"$VIRTUAL_ENV\"\``] $PS1"
    else
        PS1="(`basename \"$VIRTUAL_ENV\"`)$PS1"
    fi
    fi
    export PS1
fi

# This should detect bash and zsh, which have a hash command that must
# be called to get it to forget past commands.  Without forgetting
# past commands the $PATH changes we made may not be respected
if [ -n "${BASH:-}" -o -n "${ZSH_VERSION:-}" ] ; then
    hash -r
fi
'''
    print("removing old activate script")
    if os.path.exists(activation_bash_path):
        os.rename(activation_bash_path, activation_bash_path + "_old")

    
    with open(activation_bash_path, "w") as activate:
        activate.write(script)

    os.popen(f"chmod +x {activation_bash_path}")
    
    print("new activate_file written")

def make_request_exec_bash():
    script = "#!/bin/bash\n"
    script += f"source {activation_bash_path}\n"
    script += f"python3 {request_script_path}\n"
    script += f"deactivate"

    print(f"Bash_script:\n{script}")

    with open(request_script_bash, "w") as bash_file:
        bash_file.write(script)

    os.popen(f"chmod +x {request_script_bash}")
    print("Make script runable")


def make_run_program_bash():
    script = "#!/bin/bash\n"
    script += f"source {activation_bash_path}\n"
    script += "which python\n"
    script += f"python3 {main_program_path}\n"
    script += "echo ...deactivate\n"
    script += f"deactivate"

    print(f"Bash_script:\n{script}")

    with open(main_program_bash, "w") as bash_file:
        bash_file.write(script)

    os.popen(f"chmod +x {main_program_bash}")
    print("Make script runable")    


setup_file_path = os.path.abspath(__file__)
root_dir = os.path.abspath(os.path.join(setup_file_path, os.pardir, os.pardir))
last_file_path = os.path.abspath(os.path.join(root_dir, "last_path.txt"))
activation_bash_path = os.path.abspath(os.path.join(root_dir, "venv", "bin", "activate"))

request_script_path = os.path.abspath(os.path.join(root_dir, "Python", "Request_Skript.py"))
request_script_bash = os.path.abspath(os.path.join(root_dir, "bash", "request_script_run.bash"))


main_program_path = os.path.abspath(os.path.join(root_dir, "Python", "Diktierprogram.py"))
main_program_bash = os.path.abspath(os.path.join(root_dir, os.pardir, "Diktierprogram.bash"))

venv_location = os.path.abspath(os.path.join(root_dir, "venv"))

bash_path = os.path.abspath(os.path.join(root_dir, "bash"))

if os.path.exists(last_file_path):
    with open(last_file_path, "r") as last:
        last_file = last.read()
else:
    last_file = ""

if last_file != setup_file_path:
    print("= = = = = = = = = = Running Setup = = = = = = = = = =")
    print(f"Path of Setup: {setup_file_path}")
    print(f"Root path of Programm: {root_dir}")
    print(f"Activation Bash Path: {activation_bash_path}")
    print(f"Request Python Script: {request_script_path}")
    print(f"Request Bash Script: {request_script_bash}")

    if os.path.exists(bash_path):
        print("removing previous Scripts")
        shutil.rmtree(bash_path)
        os.mkdir(bash_path)
        
    overwrite_activate()
    make_request_exec_bash()
    make_run_program_bash()
    

else:
    print("Setup is correct")

with open(last_file_path, "w") as last:
    last.write(setup_file_path)





