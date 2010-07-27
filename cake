#!/usr/bin/python


import sys
import commands
import os
from sets import Set

class UserException (Exception):
    def __init__(self, text):
        Exception.__init__(self, text)


BUILD_COMMAND = ("gcc " +
                "-I deps/3rdparty/lwip/lwip/src/include/ipv4 " + 
                "-I deps/3rdparty/lwip/lwip/src/include " + 
                "-I deps/3rdparty/lwip/lwip/src/include " + 
                "-I deps/3rdparty/lwip/ " + 
                "-I . ")

LINK_COMMAND = "-lstdc++"

def usage():
    print >> sys.stderr, "Usage: cake [main.cpp]"
    print >> sys.stderr, "Cake is a zero-config, fast, C++ builder"
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


try:
    os.mkdir("bin")
except:
    pass


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
            result, text = extractOption(text, "//#CCFLAGS=")
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
    cmd = BUILD_COMMAND + " -MM -MF " + deps_file + " " + source_file 
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


def generate_makefile(source, output_name):
    """Given a source filename, generates a makefile"""

    sources = {}
    ignored = []
    linkflags = {}
    cause = []
    insert_dependencies(sources, ignored, source, linkflags, cause)

    lines = []    
    for s in sources:
        obj = munge(s) + ".o"
        ccflags, cause, headers = sources[s]
        
        lines.append(obj + " : " + " ".join(headers + [s]))
        lines.append("\t" + BUILD_COMMAND + " -c " + " " + s + " " " -o " + munge(s) + ".o" + " " + " ".join(ccflags))
        lines.append("")
    
    lines.append( output_name + " : " + " ".join([munge(s) + ".o" for s in  sources]) + " Makefile")
    lines.append("\t" + BUILD_COMMAND + " " + " " .join([munge(s) + ".o" for s in  sources]) + " " + LINK_COMMAND + " " + " ".join([l for l in linkflags]) + " -o " + output_name )
    lines.append("")
    
    newtext = "\n".join(lines)
    return newtext

def cpus():
    status, output = commands.getstatusoutput("cat /proc/cpuinfo | grep cpu.cores | head -1 | cut -f2 -d\":\"")
    return output.strip()

def main():
        
    if len(sys.argv) < 2:
        usage()

    source = sys.argv[1]
    output = os.path.splitext("bin/" + os.path.split(source)[1])[0]
    text = generate_makefile(source, output)
    makefilename = munge(source) + ".Makefile"
    lazily_write(makefilename, text)
    
    # make
    os.system("make -s -f " + makefilename + " " + output + " -j" + cpus())
    
    # run
    os.execvp(output, sys.argv[1:])
    return
    

try:
    main()
except SystemExit:
    raise
except KeyboardInterrupt:
    sys.exit(1)
