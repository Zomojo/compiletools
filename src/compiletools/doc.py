import configargparse
import sys
import compiletools.apptools

def main(argv=None):
    cap = compiletools.apptools.create_parser("Documentation tool", argv=argv, include_config=False)
    args = cap.parse_args(args=argv)
    print(f"Try using {sys.argv[0]} --man")

    return 0
