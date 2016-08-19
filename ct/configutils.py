import sys
import os
import zlib
import ast
import appdirs
import configargparse
import ct.wrappedos


def extract_value_from_argv(key, argv=None, default=None):
    """ Extract the value for the given key from the argv.
        Return the given default if no key was identified
    """
    if argv is None:
        argv = sys.argv

    value = default

    for arg in argv:
        try:
            keywithhyphens = "".join(['--', key, '='])
            if keywithhyphens in arg:
                value = arg.split('=')[1]
            else:
                keywithhyphens = "".join(['--', key])
                if keywithhyphens in arg:
                    index = argv.index(keywithhyphens)
                    value = argv[index + 1]
        except ValueError:
            pass
    return value


def extract_item_from_ct_conf(
        key,
        user_config_dir=None,
        system_config_dir=None,
        exedir=None,
        default=None,
        verbose=0):
    """ Extract the value for the given key from the ct.conf files.
        Return the given default if no key was identified
    """
    fileparser = configargparse.ConfigFileParser()
    for cfgpath in defaultconfigs(user_config_dir=user_config_dir,
                                  system_config_dir=system_config_dir,
                                  exedir=exedir):
        with open(cfgpath) as cfg:
            items = fileparser.parse(cfg)
            try:
                value = items[key]
                if verbose >= 2:
                    print(" ".join([cfgpath, 'contains', key, '=', value]))
                return value
            except KeyError:
                continue

    return default


def extract_variant(
        argv=None,
        user_config_dir=None,
        system_config_dir=None,
        exedir=None,
        verbose=0):
    """ The variant argument is parsed directly from the command line arguments
        so that it can be used to specify the default config for configargparse.
        Remember that the hierarchy of values is
        command line > environment variables > config file values > defaults
    """
    if argv is None:
        argv = sys.argv

    # Parse the command line, et al, extract the variant the user wants,
    # then use that as the default config file for configargparse.
    # Be careful to make use of the variant aliaes defined in the ct.conf files
    variantaliases = extract_item_from_ct_conf(
        key='variantaliases',
        user_config_dir=user_config_dir,
        system_config_dir=system_config_dir,
        exedir=exedir,
        verbose=verbose)
    if variantaliases is None:
        variantaliases = {}
    else:
        variantaliases = ast.literal_eval(variantaliases)

    variant = "debug"
    variant = extract_item_from_ct_conf(
        key='variant',
        user_config_dir=user_config_dir,
        system_config_dir=system_config_dir,
        exedir=exedir,
        default=variant,
        verbose=verbose)
    try:
        variant = os.environ['variant']
    except:
        pass
    variant = extract_value_from_argv(
        key='variant',
        argv=argv,
        default=variant)

    try:
        return variantaliases[variant]
    except KeyError:
        return variant


def variant_with_hash(
        args,
        argv=None,
        variant=None,
        user_config_dir=None,
        system_config_dir=None,
        exedir=None):
    """ Note that the argv can override the options in the config file.
        If we want to keep the differently specified flags separate then
        some hash of the argv must be added onto the config file name.
        Choose adler32 for speed
    """
    if not variant:
        variant = extract_variant(
            argv,
            user_config_dir=user_config_dir,
            system_config_dir=system_config_dir,
            exedir=exedir,
            verbose=args.verbose)

    # Only hash the bits of args that could change the build products
    unimportantkeys = [
        'clean',
        'verbose',
        'quiet',
        'auto',
        'filelist',
        'output',
        'prepend',
        'append',
        'parallel',
        'makefilename',
        'filter',
        'merge',
        'headerdeps',
        'shorten',
        'style',
        'CTCACHE']
    kwargs = {attr: value
              for attr, value in args.__dict__.items()
              if attr not in unimportantkeys}
    # The & <magicnumber> at the end is so that python2/3 give the same result
    return "%s.%08x" % (
        variant, (zlib.adler32(str(kwargs).encode('utf-8')) & 0xffffffff))


def default_config_directories(
        user_config_dir=None,
        system_config_dir=None,
        exedir=None,
        verbose=0):
    # Use configuration in the order (lowest to highest priority)
    # 1) same path as exe,
    # 2) system config (XDG compliant.  /etc/xdg/ct)
    # 3) user config   (XDG compliant. ~/.config/ct)
    # 4) environment variables
    # 5) given on the command line

    # These variables are settable to assist writing tests
    if user_config_dir is None:
        user_config_dir = appdirs.user_config_dir(appname='ct')
    if system_config_dir is None:
        system_config_dir = appdirs.site_config_dir(appname='ct')
    if exedir is None:
        exedir = ct.wrappedos.dirname(ct.wrappedos.realpath(sys.argv[0]))

    executable_config_dir = os.path.join(exedir, "ct.conf.d")
    results = [user_config_dir, system_config_dir, executable_config_dir]
    if verbose >= 9:
        print(" ".join(["Default config directories"] + results))

    return results


def defaultconfigs(
        user_config_dir=None,
        system_config_dir=None,
        exedir=None,
        verbose=0):
    ctconfs = [
        os.path.join(
            defaultdir,
            'ct.conf') for defaultdir in default_config_directories(
            user_config_dir=user_config_dir,
            system_config_dir=system_config_dir,
            exedir=exedir,
            verbose=verbose)]

    # Only return the configs that exist
    configs = [cfg for cfg in ctconfs if ct.wrappedos.isfile(cfg)]
    if verbose >= 8:
        print(" ".join(["Default configs are "] + configs))
    return configs


def config_files_from_variant(
        variant=None,
        argv=None,
        user_config_dir=None,
        system_config_dir=None,
        exedir=None):
    if variant is None:
        variant = extract_variant(argv, exedir=exedir)
    variantconfigs = [
        os.path.join(
            defaultdir,
            variant) +
        ".conf" for defaultdir in default_config_directories(
            user_config_dir=user_config_dir,
            system_config_dir=system_config_dir,
            exedir=exedir)]

    # Only return the configs that exist
    configs = [
        cfg for cfg in variantconfigs +
        defaultconfigs(
            user_config_dir=user_config_dir,
            system_config_dir=system_config_dir,
            exedir=exedir) if ct.wrappedos.isfile(cfg)]
    return configs
