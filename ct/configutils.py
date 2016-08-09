import sys
import os
import zlib
import ast
import appdirs
import configargparse
import ct.wrappedos
import ct.dirnamer

def extract_item_from_ct_conf(key, exedir=None):
    cfgdirs = default_config_directories(exedir=exedir)
    for cfgdir in cfgdirs:
        cfgpath = os.path.join(cfgdir, 'ct.conf')
        if os.path.isfile(cfgpath):
            fileparser = configargparse.ConfigFileParser()
            with open(cfgpath) as cfg:
                items = fileparser.parse(cfg)
                try:
                    return items[key]
                except KeyError:
                    continue

    return None


def extract_variant_from_argv(argv=None, exedir=None):
    """ The variant argument is parsed directly from the command line arguments
        so that it can be used to specify the default config for configargparse.
    """
    if argv is None:
        argv = sys.argv

    # Parse the command line, extract the variant the user wants, then use
    # that as the default config file for configargparse
    variantaliases = extract_item_from_ct_conf(
        key='variantaliases',
        exedir=exedir)
    if variantaliases is None:
        variantaliases = {}
    else:
        variantaliases = ast.literal_eval(variantaliases)

    variant = extract_item_from_ct_conf(key='variant', exedir=exedir)
    if variant is None:
        variant = "debug"

    for arg in argv:
        try:
            if "--variant=" in arg:
                variant = arg.split('=')[1]
            elif "--variant" in arg:
                variant_index = argv.index("--variant")
                variant = argv[variant_index + 1]
        except ValueError:
            pass

    try:
        return variantaliases[variant]
    except KeyError:
        return variant


def variant_with_hash(args, argv=None, variant=None, exedir=None):
    """ Note that the argv can override the options in the config file.
        If we want to keep the differently specified flags separate then
        some hash of the argv must be added onto the config file name.
        Choose adler32 for speed
    """
    if not variant:
        variant = extract_variant_from_argv(argv,exedir)

    # Only hash the bits of args that could change the build products
    unimportantkeys = [
        'clean',
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
        'style']
    kwargs = {attr: value 
             for attr,value in args.__dict__.iteritems() 
             if attr not in unimportantkeys}
    # The & <magicnumber> at the end is so that python2/3 give the same result
    return "%s.%08x" % (
        variant, (zlib.adler32(str(kwargs).encode('utf-8')) & 0xffffffff))


def default_config_directories(
        user_config_dir=None,
        system_config_dir=None,
        exedir=None):
    # Use configuration in the order (lowest to highest priority)
    # 1) same path as exe,
    # 2) system config (XDG compliant.  /etc/xdg/ct)
    # 3) user config   (XDG compliant. ~/.config/ct)
    # 4) given on the command line
    # 5) environment variables

    # These variables are settable to assist writing tests
    if user_config_dir is None:
        user_config_dir = ct.dirnamer.user_config_dir(appname='ct')
    if system_config_dir is None:
        system_config_dir = ct.dirnamer.site_config_dir(appname='ct')
    if exedir is None:
        exedir = ct.wrappedos.dirname(ct.wrappedos.realpath(sys.argv[0]))

    executable_config_dir = os.path.join(exedir, "ct.conf.d")

    return [user_config_dir, system_config_dir, executable_config_dir]


def config_files_from_variant(variant=None, argv=None, exedir=None):
    if variant is None:
        variant = extract_variant_from_argv(argv,exedir=exedir)
    variantconfigs = [
        os.path.join(defaultdir, variant)
        + ".conf" for defaultdir in default_config_directories(exedir=exedir)]
    defaultconfigs = [
        os.path.join(
            defaultdir,
            "ct.conf") for defaultdir in default_config_directories(
            exedir=exedir)]

    # Only return the configs that exist
    configs = [
        cfg for cfg in variantconfigs +
        defaultconfigs if ct.wrappedos.isfile(cfg)]
    return configs
