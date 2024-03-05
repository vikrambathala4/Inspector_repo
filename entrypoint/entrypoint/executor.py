import os


def invoke_command(bin, args) -> int:
    # concatenate binary and arguments
    cmd = f"{bin} {' '.join(args)}"

    # we use os.system for real time console output
    return os.system(cmd)
