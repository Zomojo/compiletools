import configargparse
import sys
import compiletools.apptools

def main(argv=None):
    cap = configargparse.getArgumentParser()
    compiletools.apptools.add_base_arguments(cap)
    args = cap.parse_args(args=argv)
    print(f"Try using {sys.argv[0]} --man")

    return 0
