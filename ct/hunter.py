from __future__ import print_function
from __future__ import unicode_literals

import os
import re
import subprocess
import sys
from io import open

import configargparse

import ct.utils
import ct.wrappedos
from ct.diskcache import diskcache
from ct.memoize import memoize
import ct.headerdeps
import ct.magicflags


def add_arguments(cap):
    """ Add the command line arguments that the Hunter classes require """
    ct.apptools.add_common_arguments(cap)
    ct.headerdeps.add_arguments(cap)
    ct.magicflags.add_arguments(cap)


class Hunter(object):

    """ Deeply inspect files to understand what are the header dependencies,
        other required source files, other required compile/link flags.
    """

    def __init__(self, args, headerdeps, magicparser):
        self.args = args
        self.headerdeps = headerdeps
        self.magicparser = magicparser

    def _extractSOURCE(self, realpath):
        sources = self.magicparser.parse(realpath).get('SOURCE', set())
        cwd = ct.wrappedos.dirname(realpath)
        ess = {ct.wrappedos.realpath(os.path.join(cwd, es)) for es in sources}
        if self.args.verbose >= 2 and ess:
            print(
                "Hunter::_extractSOURCE. realpath=",
                realpath,
                " SOURCE flag:",
                ess)
        return ess

    def _required_files_impl(self, realpath, processed=None):
        """ The recursive implementation that finds the source files.
            This function returns all headers and source files encountered.
            If you only need the source files then post process the result.
            It is a precondition that realpath actually is a realpath.
        """
        if not processed:
            processed = set()
        if self.args.verbose >= 7:
            print(
                "Hunter::_required_files_impl. Finding header deps for ",
                realpath)

        # Don't try and collapse these lines.
        # We don't want todo as a handle to the headerdeps.process object.
        todo = set()
        todo |= self.headerdeps.process(realpath)

        # One of the magic flags is SOURCE.  If that was present, add to the
        # file list.
        todo |= self._extractSOURCE(realpath)

        # The header deps and magic flags have been parsed at this point so it
        # is now safe to mark the realpath as processed.
        processed.add(realpath)

        implied = ct.utils.implied_source(realpath)
        if implied:
            todo.add(implied)

        todo -= processed
        while todo:
            if self.args.verbose >= 9:
                print(
                    "Hunter::_required_files_impl. ",
                    realpath,
                    " remaining todo:",
                    todo)
            morefiles = set()
            for nextfile in todo:
                morefiles |= self._required_files_impl(nextfile, processed)
            todo = morefiles.difference(processed)

        if self.args.verbose >= 9:
            print(
                "Hunter::_required_files_impl. ",
                realpath,
                " Returning ",
                processed)
        return processed

    @memoize
    def required_source_files(self, filename):
        """ Create the list of source files that also need to be compiled
            to complete the linkage of the given file. If filename is a source
            file itself then the returned set will contain the given filename.
            As a side effect, the magic //#... flags are cached.
        """
        if self.args.verbose >= 9:
            print("Hunter::required_source_files for " + filename)
        return {filename for filename in self.required_files(
            filename) if ct.utils.issource(filename)}

    @memoize
    def required_files(self, filename):
        """ Create the list of files (both header and source)
            that are either directly or indirectly utilised by the given file.
            The returned set will contain the original filename.
            As a side effect, examine the files to determine the magic //#... flags
        """
        if self.args.verbose >= 9:
            print("Hunter::required_files for " + filename)
        return self._required_files_impl(ct.wrappedos.realpath(filename))

    def magicflags(self, filename):
        return self.magicparser.parse(filename)

    def header_dependencies(self, source_filename):
        if self.args.verbose >= 8:
            print(
                "Hunter asking for header dependencies for ",
                source_filename)
        return self.headerdeps.process(source_filename)
