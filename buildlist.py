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

LINK_COMMAND = "-lstdc++ -lz -lboost_filesystem-gcc-mt  -lboost_program_options-gcc-mt  -lpcap -ldl -lpthread deps/3rdparty/lwip/lib/liblwip.a -lzcard -lbz2"

def usage():
    print >> sys.stderr, "Usage: buildlist.py [main.cpp]"
    print >> sys.stderr, "Generates a build list based on a single main.cpp file"
    sys.exit(1)



def get_dependencies_for(source_file):
    """Converts a gcc make command into a set of headers and source dependencies"""

    print "Getting dependencies from ",source_file

    status, output = commands.getstatusoutput(BUILD_COMMAND + " -MM -MF dependencies.tmp " + source_file)    
    if status != 0:
        raise UserException(output)

    f = open("dependencies.tmp")
    text = f.read()
    f.close()    
    
    files = text.split(":")[1]
    files = files.replace("\\", " ").replace("\t"," ").replace("\n", " ")
    files = [x for x in files.split(" ") if len(x) > 0]
    files = list(Set([os.path.normpath(x) for x in files]))
    files.sort()
    
    headers = [h for h in files if h.endswith(".hpp")]
    sources = [h for h in files if h.endswith(".cpp")]
    
    return headers, sources


def insert_dependencies(sources, ignored, new_file):
    """Given a set of sources already being compiled, inserts the new file."""
    
    if new_file in sources:
        return
        
    if new_file in ignored:
        return
        
    if not os.path.exists(new_file):
        ignored.append(new_file)
        return
        
    sources.append(new_file)
    
    # recursive step
    new_headers, new_sources = get_dependencies_for(new_file)
    for h in new_headers:
        insert_dependencies(sources, ignored, os.path.splitext(h)[0] + ".cpp")
    
    for s in new_sources:
        insert_dependencies(sources, ignored, s)


def main():
        
    if len(sys.argv) != 2:
        usage()

    sources = []
    ignored = []
    insert_dependencies(sources, ignored, sys.argv[1])
    
    print "\n".join(sources)
    os.system(BUILD_COMMAND + " " + " " .join(sources) + " " + LINK_COMMAND)
    
    

try:
    main()
except SystemExit:
    raise
except KeyboardInterrupt:
    sys.exit(1)
