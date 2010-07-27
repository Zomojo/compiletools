#!/usr/bin/python -u


import md5
import sys
import commands
import os
from sets import Set

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

def parse_etc():
    """parses /etc/cake as if it was part of the environment.
    os.environ has higher precedence
    """
    if os.path.exists("/etc/cake"):
        f = open("/etc/cake")
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
                value = value.replace("$" + k, os.environ[k])
                value = value.replace("${" + k + "}", os.environ[k])            
            
            if not key in os.environ:
                os.environ[key] = str(value)




def usage(msg = ""):
    if len(msg) > 0:
        print >> sys.stderr, msg
        print >> sys.stderr, ""
    print >> sys.stderr, "Usage: cake [main.cpp]"
    print >> sys.stderr, "Cake is a zero-config, fast, C++ builder."
    print >> sys.stderr, ""
    sys.exit(1)


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


def munge(filename):
    return "bin/" + filename.replace("/", "@")


def parse_dependencies(deps_file, source_file):
    """Parses a dependencies file"""
    
    f = open(deps_file)
    text = f.read()
    f.close()    
    
    files = text.split(":")[1]
    files = files.replace("\\", " ").replace("\t"," ").replace("\n", " ")
    files = [x for x in files.split(" ") if len(x) > 0]
    files = list(Set([os.path.normpath(x) for x in files]))
    files.sort()
    
    headers = [h for h in files if h.endswith(".hpp")]
    sources = [h for h in files if h.endswith(".cpp")]
    
    # determine ccflags and linkflags
    ccflags = {}
    linkflags = {}
    for h in headers + [source_file]:
        f = open(h)
        text = f.read(1024)        
                
        while True:
            result, text = extractOption(text, "//#CXXFLAGS=")
            if result is None:
                break
            else:
                ccflags[result] = True
        while True:
            result, text = extractOption(text, "//#LINKFLAGS=")
            if result is None:
                break
            else:
                linkflags[result] = True
                
            
        f.close()
        pass
    
    return headers, sources, ccflags, linkflags    


def get_dependencies_for(source_file):
    """Converts a gcc make command into a set of headers and source dependencies"""

    deps_file = munge(source_file) + ".deps"
    
    # try and reuse the existing if possible    
    if os.path.exists(deps_file):
        deps_mtime = os.stat(deps_file).st_mtime
        headers, sources, ccflags, linkflags  = parse_dependencies(deps_file, source_file)
    
        all_good = True
        for s in headers + [source_file]:
            try:
                if os.stat(s).st_mtime > deps_mtime:
                    all_good = False
                    break
            except: # missing file counts as a miss
                all_good = False
                break
        if all_good:
            return headers, sources, ccflags, linkflags
        
    # failed, regenerate dependencies
    cmd = CC + " -MM -MF " + deps_file + " " + source_file 
    status, output = commands.getstatusoutput(cmd)
    if status != 0:
        raise UserException(output)

    return parse_dependencies(deps_file, source_file)


def insert_dependencies(sources, ignored, new_file, linkflags, cause):
    """Given a set of sources already being compiled, inserts the new file."""
    
    if new_file in sources:
        return
        
    if new_file in ignored:
        return
        
    if not os.path.exists(new_file):
        ignored.append(new_file)
        return

    # recursive step
    new_headers, new_sources, newccflags, newlinkflags = get_dependencies_for(new_file)
    
    sources[new_file] = (newccflags, cause, new_headers)
    
    # merge in link options
    for l in newlinkflags:
        linkflags[l] = True
    
    copy = cause[:]
    copy.append(new_file)
    
    for h in new_headers:
        insert_dependencies(sources, ignored, os.path.splitext(h)[0] + ".cpp", linkflags, copy)
    
    for s in new_sources:
        insert_dependencies(sources, ignored, s, linkflags, copy)


def try_set_variant(variant):
    global CC, CXXFLAGS, LINKFLAGS
    CC = environ("CAKE_" + variant.upper() + "_CC", None)
    CXXFLAGS = environ("CAKE_" + variant.upper() + "_CXXFLAGS", None)
    LINKFLAGS = environ("CAKE_" + variant.upper() + "_LINKFLAGS", None)

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
        f.write(newtext)
        f.close()

def objectname(source, entry):
    ccflags, cause, headers = entry
    h = md5.md5(" ".join([c for c in ccflags]) + " " + CXXFLAGS).hexdigest()
    return munge(source) + str(len(str(ccflags))) + "-" + h + ".o"

def generate_makefile(source, output_name, makefile_filename):
    """Given a source filename, generates a makefile"""

    sources = {}
    ignored = []
    linkflags = {}
    cause = []
    insert_dependencies(sources, ignored, source, linkflags, cause)

    lines = []    
    for s in sources:
        obj = objectname(s, sources[s])
        ccflags, cause, headers = sources[s]
        
        lines.append(obj + " : " + " ".join(headers + [s]))
        lines.append("\t" + CC + " -c " + " " + s + " " " -o " + obj + " " + " ".join(ccflags) + " " + CXXFLAGS)
        lines.append("")
    
    lines.append( output_name + " : " + " ".join([objectname(s, sources[s]) for s in  sources]) + " " + makefile_filename)
    lines.append("\t" + CC + " " + " " .join([objectname(s, sources[s]) for s in  sources]) + " " + LINKFLAGS + " " + " ".join([l for l in linkflags]) + " -o " + output_name )
    lines.append("")
    
    newtext = "\n".join(lines)
    return newtext

def cpus():
    status, output = commands.getstatusoutput("cat /proc/cpuinfo | grep cpu.cores | head -1 | cut -f2 -d\":\"")
    return output.strip()

def do_generate(source, output):
    makefilename = munge(source) + ".Makefile"
    text = generate_makefile(source, output, makefilename)
    lazily_write(makefilename, text)
    
def do_build(source, output, quiet):
    makefilename = munge(source) + ".Makefile"
    result = os.system("make " + {True:"-s ",False:""}[quiet] + "-f " + makefilename + " " + output + " -j" + cpus())
    if result != 0:
        sys.exit(result)

def do_run(output, args):
    os.execvp(output, [output] + args)




def main():
    global CC, CXXFLAGS, LINKFLAGS
        
    if len(sys.argv) < 2:
        usage()
        
    # parse arguments
    args = sys.argv[1:]
    cppfile = None
    appargs = []
    output = None
    
    generate = True
    build = True
    run = True
    quiet = False
    
    for a in args:        
        if cppfile is None:            
            if a.startswith("--CC="):
                CC = a[a.index("=")+1:]
                continue
            
            if a.startswith("--output="):
                output = a[a.index("=")+1:]
                continue
                
            if a.startswith("--variant="):
                variant = a[a.index("=")+1:]      
                try_set_variant(variant)
                continue
                
            if a.startswith("--quiet"):
                quiet = True
                continue
                
            if a == "--generate":
                generate = True
                build = False
                run = False
                continue
            
            if a == "--build":
                generate = True
                build = True
                run = False
                continue
                
            if a == "--run":
                generate = True
                build = True
                run = False
                continue
            
            if a.startswith("--LINKFLAGS="):
                LINKFLAGS = a[a.index("=")+1:]
                continue
            
            if a.startswith("--CXXFLAGS="):
                CXXFLAGS = a[a.index("=")+1:]
                continue
            
            if a.startswith("--"):
                usage("Invalid option " + a)
        
            cppfile = a
        else:
            appargs.append(a)
    
    if cppfile is None:
        usage("You must specify a filename.")
    
    if not os.path.exists(cppfile):
        print >> sys.stderr, cppfile + " not found."
        sys.exit(1)

    if output is None:
        output = os.path.splitext("bin/" + os.path.split(cppfile)[1])[0]
    
    if generate:
        do_generate(cppfile, output)
    
    if build:
        do_build(cppfile, output, quiet)
        
    if run:
        do_run(output, appargs)
    return
    

try:
    
    # data
    CC = "g++"
    LINKFLAGS = ""
    CXXFLAGS = ""
    parse_etc()
    CC = environ("CAKE_CC", CC)
    LINKFLAGS = environ("CAKE_LINKFLAGS", LINKFLAGS)
    CXXFLAGS = environ("CAKE_CXXFLAGS", CXXFLAGS)

    try:
        os.mkdir("bin")
    except:
        pass

    
    main()
except SystemExit:
    raise
except UserException, e:
    print >> sys.stderr, str(e)
    sys.exit(1)
except KeyboardInterrupt:
    sys.exit(1)
