import configargparse
import ct.apptools

def main(argv=None):
    cap = configargparse.getArgumentParser()
    ct.apptools.add_base_arguments(cap)
    args = cap.parse_args(args=argv)
    if args.verbose >= 1:
        ct.apptools.verbose_print_args(args)

    return 0
