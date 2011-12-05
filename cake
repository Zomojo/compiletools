#!/usr/bin/python -u

import cPickle
import sys
import commands
import os

if sys.version_info < (2,6):
    from sets import Set
    set = Set


if sys.version_info < (2,6):
    import md5 as cake_hasher
else:
    import hashlib as cake_hasher


BINDIR="bin/"
OBJDIR=""
verbose = False
debug = False

class OrderedSet:
    """A set that preserves the order of insertion"""

    def __init__(self, init = ()):
        self.ordered = []
        self.unordered = {}

        for s in init:
            self.insert(s)

    def insert(self, e):
        if e in self.unordered:
            return
        self.ordered.append(e)
        self.unordered[e] = True
    
    def __repr__(self):
        return repr(self.ordered)
        
    def __contains__(self, e):
        return self.unordered.__contains__(e)
        
    def __len__(self):
        return self.ordered.__len__()
        
    def __iter__(self):
        return self.ordered.__iter__()
             
        


class UserException (Exception):
    def __init__(self, text):
        Exception.__init__(self, text)



def environ(variable, default):
    if default is None:
        if not variable in os.environ:
            raise UserException("Couldn't find required environment variable " + variable)
        return os.environ[variable]
    else:
        if not variable in os.environ:
            return default
        else:
            return os.environ[variable]

def parse_etc(config_file):
    """parses /etc/cake as if it was part of the environment.
    os.environ has higher precedence
    """

    global debug

    if stat(config_file):
        f = open(config_file)
        lines = f.readlines()
        f.close()

        for l in lines:
            if l.startswith("#"):
                continue
            l = l.strip()

            if len(l) == 0:
                continue
            key = l[0:l.index("=")].strip()
            value = l[l.index("=") + 1:].strip()

            for k in os.environ:
                value = value.replace('"', "")
                value = value.replace("$" + k, os.environ[k])
                value = value.replace("${" + k + "}", os.environ[k])

            if not key in os.environ:
                os.environ[key] = str(value)


usage_text = """

Usage: cake [compilation args] filename.cpp [app args]

cake generates and runs C++ executables with almost no configuration.

Options:

    --help                 Shows this message.
    --quiet                Doesn't output progress messages.
    --verbose              Outputs the result of build commands (doesn't run make with -s)
    --cake-debug           Output extra cake specific info.
    --config               Specify the config file to use.

    --bindir               Specifies the directory to contain binary executable outputs. Defaults to 'bin'.
    --objdir               Specifies the directory to contain object intermediate files. Defaults to 'bin/obj'.
    --generate             Only runs the makefile generation step, does not build.
    --build                Builds the given targets (default).
    --output=<filename>    Overrides the output filename.
    --variant=<vvv>        Reads the CAKE_<vvv>_CC, CAKE_<vvv>_CXXFLAGS and CAKE_<vvv>_LINKFLAGS
                           environment variables to determine the build flags.

    --CC=<compiler>        Sets the C compiler command.
    --CPP=<compiler>       Sets the C++ compiler command.
    --LINKER=<linker>      Sets the linker command.
    --ID=<id>              Sets the prefix to the embedded source annotations, and a predefined macro CAKE_${ID}
    --CXXFLAGS=<flags>     Sets the compilation flags for all c and cpp files in the build.
    --TESTPREFIX=<cmd>     Runs tests with the given prefix, eg. "valgrind --quiet --error-exitcode=1"
    --POSTPREFIX=<cmd>     Runs post execution commands with the given prefix, eg. "timeout 60"
    --LINKFLAGS=<flags>    Sets the flags used while linking.

    --append-CC=...        Appends the given text to the C compiler commands. Use for adding search paths etc.
    --append-CPP=...       Appends the given text to the C++ compiler commands. Use for adding search paths etc.
    --append-CXXFLAGS=...  Appends the given text to the CXXFLAGS already set. Use for adding search paths etc.
    --append-LINKFLAGS=..  Appends the given text to the LINKFLAGS already set. Use for example with `wx-config --libs`

    --bindir=...           Overrides the directory where binaries are produced. 'bin/' by default.

    --begintests           Starts a test block. The cpp files following this declaration will
                           generate executables which are then run.

    --endtests             Ends a test block.

    --beginpost            Starts a post execution block. The commands given after this will be
                           run verbatim after each build. Useful for running integration tests,
                           or generating tarballs, uploading to a website etc.
    --endpost              Ends a post execution block.


Source annotations (embed in your hpp and cpp files as magic comments):

     //#{flag prefix}CXXFLAGS=<flags>   Appends the given options to the compile step.
     //#{flag prefix}LINKFLAGS=<flags>  Appends the given options to the link step

     If no variant specific annotations are found, then the global variants are also
     searched. This allows default behaviour to be specified, while allowing
     for a particular variant as well.

Environment Variables:

    CAKE_CC                Sets the C compiler command.
    CAKE_CPP               Sets the C++ compiler command.
    CAKE_LINKER            Sets the linker command.
    CAKE_CXXFLAGS          Sets the compilation flags for all cpp files in the build.
    CAKE_LINKFLAGS         Sets the flags used while linking.
    CAKE_ID                Sets the prefix to the embedded source annotations and predefined build macro.
    CAKE_TESTPREFIX        Sets the execution prefix used while running unit tests.
    CAKE_POSTPREFIX        Sets the execution prefix used while running post-build commands.
    CAKE_BINDIR            Sets the directory where all binary files will be created.
    CAKE_OBJDIR            Sets the directory where all object files will be created.

Environment variables can also be set in /etc/cake.conf, which has the lowest priority when finding
compilation settings.


Example usage:

This command-line generates bin/prime-factoriser and bin/frobnicator in release mode.
It also generates several tests into the bin directory and runs them. If they are
all successful, integration_test.sh is run.

   cake apps/prime-factoriser.cpp apps/frobnicator.cpp \\
        --begintests tests/*.cpp --endtests \\
        --beginpost ./integration_test.sh \\
        --variant=release



"""


def usage(msg = ""):
    if len(msg) > 0:
        print >> sys.stderr, msg
        print >> sys.stderr, ""

    print >> sys.stderr, usage_text.strip() + "\n"

    sys.exit(1)


def printCakeVariables():
    print "  CC        : " + CC
    print "  CPP       : " + CPP
    print "  LINKER    : " + LINKER
    print "  ID        : " + CAKE_ID
    print "  CXXFLAGS  : " + CXXFLAGS
    print "  LINKFLAGS : " + LINKFLAGS
    print "  TESTPREFIX: " + TESTPREFIX
    print "  POSTPREFIX: " + POSTPREFIX
    print "\n"


def extractOption(text, option):
    """Extracts the given option from the text, returning the value
    on success and the trimmed text as a tuple, or (None, originaltext)
    on no match.
    """

    try:
        length = len(option)
        start = text.index(option)
        end = text.index("\n", start + length)
        
        result = text[start + length:end]
        trimmed = text[:start] + text[end+1:]
        return result, trimmed
        
    except ValueError:
        return None, text


realpath_cache = {}
def realpath(x):
    global realpath_cache
    #print "BEGIN ",x
    if not x in realpath_cache:
        realpath_cache[x] = os.path.realpath(x)
    return realpath_cache[x]


def munge(to_munge):
    if isinstance(to_munge, dict):
        if len(to_munge) == 1:
            return OBJDIR + "@@".join([realpath(x) for x in to_munge]).replace("/", "@")
        else:
            return OBJDIR + cake_hasher.md5(str([realpath(x) for x in to_munge])).hexdigest()
    else:
        return OBJDIR + realpath(to_munge).replace("/", "@")


def force_get_dependencies_for(deps_file, source_file, quiet, verbose):
    """Recalculates the dependencies and caches them for a given source file"""

    global CAKE_ID
    
    if not quiet:
        print "... " + source_file + " (dependencies)"
    
    cmd = CPP + " -DCAKE_DEPS -MM -MF " + deps_file + ".tmp " + source_file

    if verbose:
        print cmd

    status, output = commands.getstatusoutput(cmd)
    if status != 0:
        raise UserException(cmd + "\n" + output)

    f = open(deps_file + ".tmp")
    text = f.read()
    f.close()
    os.unlink(deps_file + ".tmp")

    files = text.split(":")[1]
    files = files.replace("\\", " ").replace("\t"," ").replace("\n", " ")
    files = [x for x in files.split(" ") if len(x) > 0]
    files = list(set([realpath(x) for x in files]))
    files.sort()

    headers = [realpath(h) for h in files if h.endswith(".hpp") or h.endswith(".h")]
    sources = [realpath(h) for h in files if h.endswith(".cpp") or h.endswith(".c")]

    # determine ccflags and linkflags
    ccflags = {}
    linkflags = OrderedSet()

    explicit_cxx = "//#" + CAKE_ID + "_CXXFLAGS="
    explicit_link = "//#" + CAKE_ID + "_LINKFLAGS="
    explicit_glob_cxx = "//#CXXFLAGS="
    explicit_glob_link = "//#LINKFLAGS="

    for h in headers + [source_file]:
        path = os.path.split(h)[0]
        f = open(h)

        # reading and handling as one string is slightly faster then
        # handling a list of strings
        text = f.read(2048)

        found = False

        # first check for variant specific flags
        if len(CAKE_ID) > 0:
            while True:
                result, text = extractOption(text, explicit_cxx)
                if result is None:
                    break
                else:
                    if debug:
                        print "explicit " + explicit_cxx + " = '" + result + "' for " + h
                    result = result.replace("${path}", path)
                    ccflags[result] = True
                    found = True
            while True:
                result, text = extractOption(text, explicit_link)
                if result is None:
                    break
                else:
                    if debug:
                        print "explicit " + explicit_link + " = '" + result + "' for " + h
                    linkflags.insert(result.replace("${path}", path))
                    found = True

        # if none, then check globals
        if not found:
            while True:
                result, text = extractOption(text, explicit_glob_cxx)
                if result is None:
                    break
                else:
                    if debug:
                        print "explicit " + explicit_glob_cxx + " = '" + result + "' for " + h
                    result = result.replace("${path}", path)
                    ccflags[result] = True
            while True:
                result, text = extractOption(text, explicit_glob_link)
                if result is None:
                    break
                else:
                    if debug:
                        print "explicit " + explicit_glob_link + " = '" + result + "' for " + h
                    linkflags.insert(result.replace("${path}", path))

        f.close()
        pass

    # cache
    f = open(deps_file, "w")
    cPickle.dump((headers, sources, ccflags, linkflags), f)
    f.close()
    if deps_file in stat_cache:
        del stat_cache[deps_file]
    if deps_file in realpath_cache:
        del realpath_cache[deps_file]
    
    return headers, sources, ccflags, linkflags


stat_cache = {}
def stat(f):
    if not f in stat_cache:
        try:
            stat_cache[f] = os.stat(f)
        except OSError:
            stat_cache[f] = None
    return stat_cache[f]

dependency_cache = {}


def get_dependencies_for(source_file, quiet, verbose):
    """Converts a gcc make command into a set of headers and source dependencies"""    
    
    global dependency_cache

    if source_file in dependency_cache:
        return dependency_cache[source_file]

    deps_file = munge(source_file) + ".deps"

    # try and reuse the existing if possible
    deps_stat = stat(deps_file)
    if deps_stat:
        deps_mtime = deps_stat.st_mtime
        all_good = True
        
        try:
            f = open(deps_file)            
            headers, sources, ccflags, linkflags  = cPickle.load(f)
            f.close()
        except:
            all_good = False

        if all_good:
            for s in headers + [source_file]:
                try:
                    if stat(s).st_mtime > deps_mtime:
                        all_good = False
                        break
                except: # missing file counts as a miss
                    all_good = False
                    break
        if all_good:
            result = headers, sources, ccflags, linkflags
            dependency_cache[source_file] = result
            return result

    # failed, regenerate dependencies
    result = force_get_dependencies_for(deps_file, source_file, quiet, verbose)
    dependency_cache[source_file] = result
    return result


def insert_dependencies(sources, ignored, new_file, linkflags, cause, quiet, verbose):
    """Given a set of sources already being compiled, inserts the new file."""
    
    if not new_file.startswith("/"):
        raise Exception("bad")    
    
    if new_file in sources:
        return
        
    if new_file in ignored:
        return
        
    if stat(new_file) is None:
        ignored.append(new_file)
        return

    # recursive step
    new_headers, new_sources, newccflags, newlinkflags = get_dependencies_for(new_file, quiet, verbose)
    
    sources[realpath(new_file)] = (newccflags, cause, new_headers)
    
    # merge in link options
    for l in newlinkflags:
        linkflags.insert(l)
    
    copy = cause[:]
    copy.append(new_file)
    
    for h in new_headers:
        insert_dependencies(sources, ignored, os.path.splitext(h)[0] + ".cpp", linkflags, copy, quiet, verbose)
        insert_dependencies(sources, ignored, os.path.splitext(h)[0] + ".c", linkflags, copy, quiet, verbose)

    for s in new_sources:
        insert_dependencies(sources, ignored, s, linkflags, copy, quiet, verbose)


def try_set_variant(variant):
    global Variant, CC, CPP, CXXFLAGS, LINKFLAGS, TESTPREFIX, POSTPREFIX, CAKE_ID
    Variant = "CAKE_" + variant.upper()
    CC = environ(Variant + "_CC", None)
    CPP = environ(Variant + "_CPP", None)
    CAKE_ID = environ(Variant + "_ID", "")
    CXXFLAGS = environ(Variant + "_CXXFLAGS", None)
    LINKFLAGS = environ(Variant + "_LINKFLAGS", None)
    TESTPREFIX = environ(Variant + "_TESTPREFIX", None)
    POSTPREFIX = environ(Variant + "_POSTPREFIX", None)
    if debug:
        print "\n"
        print "  variant   : " + Variant


def lazily_write(filename, newtext):
    oldtext = ""
    try:
        f = open(filename)
        oldtext = f.read()
        f.close()
    except:
        pass        
    if newtext != oldtext:
        f = open(filename, "w")
        if filename in stat_cache:
            del stat_cache[filename]
        if filename in realpath_cache:
            del realpath_cache[filename]
        f.write(newtext)
        f.close()


ignore_option_mash = [ '-fprofile-generate', '-fprofile-use' ]
def objectname(source, entry):
    ccflags, cause, headers = entry
    mash_name = "".join(ccflags) + " " + CXXFLAGS + " "

    if source.endswith(".c"):
        mash_name += CC
    else:
        mash_name += CPP

    o = mash_name.split();
    o.sort()
    mash_inc = ""

    for s in o:
        if not s in ignore_option_mash:
            mash_inc += s
        else:
            mash_inc += 'ignore'

    h = cake_hasher.md5( mash_inc ).hexdigest()
    return munge(source) + str(len(str(mash_inc))) + "-" + h + ".o"



def generate_rules(source, output_name, generate_test, makefilename, quiet, verbose, static_library):
    """
    Generates a set of make rules for the given source.
    If generate_test is true, also generates a test run rule.
    """

    global Variant

    rules = {}
    sources = {}
    ignored = []
    linkflags = OrderedSet()
    cause = []
    
    source = realpath(source)
    insert_dependencies(sources, ignored, source, linkflags, cause, quiet, verbose)
    
    # compile rule for each object
    for s in sources:
        obj = objectname(s, sources[s])
        ccflags, cause, headers = sources[s]

        definition = []
        definition.append(obj + " : " + " ".join(headers + [s]))
        if not quiet:
            definition.append("\t" + "@echo ... " + s)
        if s.endswith(".c"):
            definition.append("\t" + CC + " " + CXXFLAGS + " " + " ".join(ccflags) + " -c " + " " + s + " " " -o " + obj)
        else:
            definition.append("\t" + CPP + " " + CXXFLAGS + " " + " ".join(ccflags) + " -c " + " " + s + " " " -o " + obj)

        rules[obj] = "\n".join(definition)

    # link rule
    definition = []
    tmp_output_name = OBJDIR + Variant + "/" + os.path.split(output_name)[-1]
    definition.append( tmp_output_name + " : " + " ".join([objectname(s, sources[s]) for s in  sources]) + " " + makefilename)
    linker_line = "\t" + LINKER + " "  
    if not static_library:
        linker_line += "-o "
    linker_line +=  tmp_output_name + " " + " " .join([objectname(s, sources[s]) for s in  sources])  + " " 
    if not static_library:
        linker_line += LINKFLAGS + " " + " ".join(linkflags)
    definition.append( linker_line )    
        
    definition.append( "\n.PHONY : " + output_name )
    definition.append( "\n" + output_name + " : " + tmp_output_name )
    if not quiet:
        definition.append("\t" + "@echo ... " + output_name)
    definition.append( "\tcp " + tmp_output_name + " " + output_name )


    rules[output_name] = "\n".join(definition)

    if generate_test:
        definition = []
        test = munge(output_name) + ".result"
        definition.append( test + " : " + tmp_output_name )
        if not quiet:
            definition.append("\t" + "@echo ... test " + output_name)

        t = ""
        if TESTPREFIX != "":
            t = TESTPREFIX + " "
        definition.append( "\t" + "rm -f " + test + " && " + t + tmp_output_name + " && touch " + test)
        rules[test] = "\n".join(definition)

    return rules


def render_makefile(makefilename, rules):
    """Renders a set of rules as a makefile"""
    
    rules_as_list = [rules[r] for r in rules]
    rules_as_list.sort()
    
    objects = [r for r in rules]
    objects.sort()
    
    # top-level build rule
    text = []
    text.append("all : " + " ".join(objects))
    text.append("")
    
    for rule in rules_as_list:
        text.append(rule)
        text.append("")        
    
    text = "\n".join(text)
    lazily_write(makefilename, text)


def cpus():
    f = open("/proc/cpuinfo")
    t = [x for x in f.readlines() if x.startswith("processor")]
    f.close()
    return str(len(t))


def do_generate(source_to_output, tests, post_steps, quiet, verbose, static_library):
    """Generates all needed makefiles"""
    global Variant

    all_rules = {}
    for source in source_to_output:
        makefilename = munge(source) + "." + Variant + ".Makefile"
        rules = generate_rules(source, source_to_output[source], source_to_output[source] in tests, makefilename, quiet, verbose, static_library)
        all_rules.update(rules)
        render_makefile(makefilename, rules)

    combined_filename = munge(source_to_output) + "." + Variant + ".combined.Makefile"

    all_previous = [r for r in all_rules]
    previous = all_previous

    post_with_space = POSTPREFIX.strip()
    if len(post_with_space) > 0:
        post_with_space = POSTPREFIX + " "

    for s in post_steps:
        passed = OBJDIR + cake_hasher.md5(s).hexdigest() + ".passed"
        rule = passed + " : " + " ".join(previous + [s]) + "\n"
        if not quiet:
            rule += "\t" + "echo ... post " + post_with_space + s
        rule += "\trm -f " + passed + " && " + post_with_space + s + " && touch " + passed
        all_rules[passed] = rule
        previous =  all_previous + [s]

    render_makefile(combined_filename, all_rules)
    return combined_filename


def do_build(makefilename, verbose):
    result = os.system("make -r " + {False:"-s ",True:""}[verbose] + "-f " + makefilename + " -j" + cpus())
    if result != 0:
        sys.exit(1)


def do_run(output, args):
    os.execvp(output, [output] + args)


def main(config_file):
    global CC, CPP, LINKER, CAKE_ID, CXXFLAGS, LINKFLAGS, TESTPREFIX, POSTPREFIX
    global BINDIR, OBJDIR
    global verbose, debug
    global Variant

    if len(sys.argv) < 2:
        usage()

    # parse arguments
    args = sys.argv[1:]
    appargs = []
    nextOutput = None

    generate = True
    build = True
    quiet = False
    static_library = False
    to_build = {}
    inTests = False
    inPost = False
    tests = []
    post_steps = []
    append_cc_flags = ''
    append_cpp_flags = ''
    append_link_flags = ''

    # set verbose and check for help
    # copy list so we can remove from the original and still iterate
    for a in list(args):
        if a == "--verbose":
            verbose = True
            args.remove(a)
        elif a == "--cake-debug":
            debug = True
            args.remove(a)
        elif a == "--static-library":
            static_library = True
            LINKER = "ar -src"
            args.remove(a)            
        elif a == "--help":
            usage()
            return

    # deal with variant next
    # to set the base set of flags for the other options to apply to
    # copy list so we can remove from the original and still iterate
    for a in list(args):
        if a.startswith("--variant="):
            variant = a[a.index("=")+1:]
            try_set_variant(variant)
            args.remove(a)
            continue

    for a in args:
        if a.startswith("--config="):
            config_file = a[a.index("=")+1:]
            continue;

        if a.startswith("--CC="):
            CC = a[a.index("=")+1:]
            continue

        if a.startswith("--LINKER="):
            LINKER = a[a.index("=")+1:]
            continue

        if a.startswith("--CPP="):
            CPP = a[a.index("=")+1:]
            continue

        if a.startswith("--ID="):
            CAKE_ID = a[a.index("=")+1:]
            continue

        if a.startswith("--bindir="):
            BINDIR = a[a.index("=")+1:]
            if not BINDIR.endswith("/"):
                BINDIR = BINDIR + "/"
            continue

        if a.startswith("--objdir="):
            OBJDIR = a[a.index("=")+1:]
            if not OBJDIR.endswith("/"):
                OBJDIR = OBJDIR + "/"
            continue

        if a.startswith("--quiet"):
            quiet = True
            continue

        if a == "--generate":
            generate = True
            build = False
            continue

        if a == "--build":
            generate = True
            build = True
            continue

        if a.startswith("--LINKFLAGS="):
            LINKFLAGS = a[a.index("=")+1:]
            continue

        if a.startswith("--append-LINKFLAGS="):
            LINKFLAGS += " " + a[a.index("=")+1:]
            continue

        if a.startswith("--TESTPREFIX="):
            TESTPREFIX = a[a.index("=")+1:]
            continue

        if a.startswith("--POSTPREFIX="):
            POSTPREFIX = a[a.index("=")+1:]
            continue

        if a.startswith("--append-CC="):
            append_cc_flags += " "
            append_cc_flags += a[a.index("=")+1:]
            continue

        if a.startswith("--append-CPP="):
            append_cpp_flags += " "
            append_cpp_flags += a[a.index("=")+1:]
            continue

        if a.startswith("--CXXFLAGS="):
            CXXFLAGS = " " + a[a.index("=")+1:]
            continue

        if a.startswith("--append-CXXFLAGS="):
            CXXFLAGS += " " + a[a.index("=")+1:]
            continue

        if a == "--beginpost":
            if inTests:
                usage("--beginpost cannot occur inside a --begintests block")
            inPost = True
            continue

        if a == "--endpost":
            inPost = False
            continue

        if a == "--begintests":
            if inPost:
                usage("--begintests cannot occur inside a --beginpost block")
            inTests = True
            continue

        if a == "--endtests":
            if not inTests:
                usage("--endtests can only follow --begintests")
            inTests = False
            continue

        if a.startswith("--output="):
            nextOutput = a[a.index("=")+1:]
            continue

        if a.startswith("--"):
            usage("Invalid option " + a)

        if nextOutput is None:
            nextOutput = os.path.splitext(BINDIR + os.path.split(a)[1])[0]
            if static_library:
                nextOutput = os.path.splitext(BINDIR + "lib" + os.path.split(a)[1])[0] + ".a"

        if inPost:
            post_steps.append(a)
        else:
            to_build[a] = nextOutput
            if inTests:
                tests.append(nextOutput)
        nextOutput = None

    if len(Variant) == 0:
        Variant = "CAKE"

    # default objdir
    if OBJDIR == "":
        OBJDIR = BINDIR

    if len(CAKE_ID) > 0:
        OBJDIR += CAKE_ID + "/"
        CXXFLAGS += " -DCAKE_" + CAKE_ID
    else:
        OBJDIR += "CAKE/"

    # compiler takes extra options, seems counter-intuitive to put into CC
    # rather than CXXFLAGS, but this allows options like -fprofile-generate
    # to work
    if len(append_cc_flags) > 0:
        CC = CC + " " + append_cc_flags

    if len(append_cpp_flags) > 0:
        CPP = CPP + " " + append_cpp_flags

    if debug:
        printCakeVariables()

    if len(to_build) == 0:
        usage("You must specify a filename.")

    try:
        os.makedirs(OBJDIR + Variant)
    except:
        pass

    try:
        os.makedirs(BINDIR)
    except:
        pass

    
    for c in to_build.keys()[:]:
        if len(c.strip()) == 0:
            del to_build[c]
            continue

        if not stat(c):
            print >> sys.stderr, c + " is not found."
            sys.exit(1)

    if generate:
        makefilename = do_generate(to_build, tests, post_steps, quiet, verbose, static_library)

    if build:
        do_build(makefilename, verbose)
    return


try:

    # data
    config_file = "/etc/cake.conf"
    Variant = ""

    CC = "g++"
    CPP = "g++"
    LINKER = "g++"
    CAKE_ID = ""
    LINKFLAGS = ""
    CXXFLAGS = ""
    TESTPREFIX=""
    POSTPREFIX=""
    BINDIR="bin/"
    OBJDIR=""

    # deal with config file first
    for a in list(sys.argv[1:]):
        if a.startswith("--config="):
            config_file = a[a.index("=")+1:]
            break

    parse_etc( config_file )

    BINDIR = environ("CAKE_BINDIR", BINDIR)
    OBJDIR = environ("CAKE_OBJDIR", OBJDIR)
    CC = environ("CAKE_CC", CC)
    CPP = environ("CAKE_CPP", CPP)
    LINKER = environ("CAKE_LINKER", LINKER)
    CAKE_ID = environ("CAKE_ID", CAKE_ID)
    LINKFLAGS = environ("CAKE_LINKFLAGS", LINKFLAGS)
    CXXFLAGS = environ("CAKE_CXXFLAGS", CXXFLAGS)
    TESTPREFIX = environ("CAKE_TESTPREFIX", TESTPREFIX)
    POSTPREFIX = environ("CAKE_POSTPREFIX", POSTPREFIX)

    main(config_file)

except SystemExit:
    raise
except IOError,e :
    print >> sys.stderr, str(e)
    sys.exit(1)
except UserException, e:
    print >> sys.stderr, str(e)
    sys.exit(1)
except KeyboardInterrupt:
    sys.exit(1)

