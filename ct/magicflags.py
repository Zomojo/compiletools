from __future__ import print_function
from __future__ import unicode_literals

import sys
import os
import subprocess
import re
import configargparse
from io import open
from ct.diskcache import diskcache
from ct.memoize import memoize
import ct.utils
import ct.git_utils
import ct.headerdeps


def create(args, headerdeps):
    """ MagicFlags Factory """
    classname = args.magic.title() + 'MagicFlags'
    if args.verbose >= 4:
        print("Creating " + classname + " to process magicflags.")
    magicclass = globals()[classname]
    magicobject = magicclass(args, headerdeps)
    return magicobject


def add_arguments(cap,variant=None):
    """ Add the command line arguments that the MagicFlags classes require """
    ct.apptools.add_common_arguments(cap, variant=variant)
    ct.preprocessor.PreProcessor.add_arguments(cap)
    alldepscls = [st[:-10].lower()
                  for st in dict(globals()) if st.endswith('MagicFlags')]
    cap.add(
        '--magic',
        choices=alldepscls,
        default='direct',
        help="Methodology for reading file when processing magic flags")


class MagicFlagsBase:

    """ A magic flag in a file is anything that starts
        with a //# and ends with an =
        E.g., //#key=value1 value2

        Note that a magic flag is a C++ comment.

        This class is a map of filenames
        to the map of all magic flags for that file.
        Each magic flag has a set of values.
        E.g., { '/somepath/libs/base/somefile.hpp':
                   {'CPPFLAGS':set('-D MYMACRO','-D MACRO2'),
                    'CXXFLAGS':set('-fsomeoption'),
                    'LDFLAGS':set('-lsomelib')}}
        This function will extract all the magics flags from the given
        source (and all its included headers).
        source_filename must be an absolute path
    """

    def __init__(self, args, headerdeps):
        self._args = args
        self._headerdeps = headerdeps

        # The magic pattern is //#key=value with whitespace ignored
        self.magicpattern = re.compile(
            '^[\s]*//#([\S]*?)[\s]*=[\s]*(.*)',
            re.MULTILINE)

    def readfile(self, filename):
        """ Derived classes implement this method """
        raise NotImplemented

    def __call__(self, filename):
        return self.parse(filename)

    def _parse(self, filename):
        if self._args.verbose >= 4:
            print("Parsing magic flags for " + filename)

        # diskcache assumes that headerdeps _always_ exist
        # before the magic flags are called.
        # When used in the "usual" fashion this is true.
        # However, it is possible to call directly so we must
        # ensure that the headerdeps exist manually.
        self._headerdeps.process(filename)

        text = self.readfile(filename)
        flagsforfilename = {}

        for match in self.magicpattern.finditer(text):
            magic, flag = match.groups()

            # If the magic was SOURCE then fix up the path
            if magic == 'SOURCE':
                # Find the include before the //#SOURCE=
                result = re.search(
                    '# \d.* "(/\S*?)".*?//#SOURCE\s*=\s*' +
                    flag,
                    text,
                    re.DOTALL)
                # Now adjust the flag to include the full path
                newflag = os.path.join(
                    ct.wrappedos.dirname(
                        result.group(1)),
                    flag)
                if self._args.verbose >= 9:
                    print(' '.join(['Adjusting source magicflag from flag=',flag,'to',newflag]))
                flag = newflag

            flagsforfilename.setdefault(magic, set()).add(flag)
            if self._args.verbose >= 5:
                print(
                    "Using magic flag {0}={1} extracted from {2}".format(
                        magic,
                        flag,
                        filename))

        return flagsforfilename


class DirectMagicFlags(MagicFlagsBase):

    def readfile(self, filename):
        """ Read the first chunk of the file and all the headers it includes """
        # reading and handling as one string is slightly faster than
        # handling a list of strings.
        # Only read the top part of the files for speed
        headers = self._headerdeps.process(filename)
        text = ""
        for filename in headers | {filename}:
            if self._args.verbose >= 9:
                print('DirectMagicFlags::readfile is inserting # ' + filename)
            with open(filename, encoding='utf-8', errors='ignore') as ff:
                # To match the output of the C Pre Processor we insert
                # the filename before the text
                text += '# 1 "'
                text += ct.wrappedos.realpath(filename)
                text += '"\n'
                text += ff.read(4096)

        return text

    @diskcache('directmagic', magic_mode=True)
    def parse(self, filename):
        return self._parse(filename)


class CppMagicFlags(MagicFlagsBase):

    def __init__(self, args, headerdeps):
        MagicFlagsBase.__init__(self, args, headerdeps)
        self.preprocessor = ct.preprocessor.PreProcessor(args)

    def readfile(self, filename):
        """ Preprocess the given filename but leave comments """
        extraargs = '-C -E'
        return self.preprocessor.process(realpath=filename,
                                         extraargs='-C -E',
                                         redirect_stderr_to_stdout=True)

    @diskcache('cppmagic', magic_mode=True)
    def parse(self, filename):
        return self._parse(filename)


class NullStyle(ct.git_utils.NameAdjuster):

    def __init__(self, args):
        ct.git_utils.NameAdjuster.__init__(self, args)

    def __call__(self, realpath, magicflags):
        print("{}: {}".format(self.adjust(realpath), str(magicflags)))


class PrettyStyle(ct.git_utils.NameAdjuster):

    def __init__(self, args):
        ct.git_utils.NameAdjuster.__init__(self, args)

    def __call__(self, realpath, magicflags):
        sys.stdout.write("\n{}".format(self.adjust(realpath)))
        try:
            for key in magicflags:
                sys.stdout.write("\n\t{}:".format(key))
                for flag in magicflags[key]:
                    sys.stdout.write(" {}".format(flag))
        except TypeError:
            sys.stdout.write("\n\tNone")


def main(argv=None):
    cap = configargparse.getArgumentParser()
    ct.headerdeps.add_arguments(cap)
    add_arguments(cap)
    cap.add(
        "filename",
        help='File/s to extract magicflags from"',
        nargs='+')

    # Figure out what style classes are available and add them to the command
    # line options
    styles = [st[:-5].lower()
              for st in dict(globals()) if st.endswith('Style')]
    cap.add(
        '--style',
        choices=styles,
        default='pretty',
        help="Output formatting style")

    args = ct.apptools.parseargs(cap, argv)
    headerdeps = ct.headerdeps.create(args)
    magicparser = create(args, headerdeps)

    styleclass = globals()[args.style.title() + 'Style']
    styleobject = styleclass(args)

    for fname in args.filename:
        realpath = ct.wrappedos.realpath(fname)
        styleobject(realpath, magicparser.parse(realpath))

    print()
    return 0
