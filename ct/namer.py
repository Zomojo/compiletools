import os
from ct.memoize import memoize
import ct.wrappedos
import ct.git_utils
import ct.utils
import ct.apptools
import ct.configutils

class Namer(object):

    """ From a source filename, calculate related names
        like executable name, object name, etc.
    """
    def __init__(self, args, argv=None, variant=None, exedir=None):
        self.args = args
        self._project = ct.git_utils.Project(args)

    @staticmethod
    def add_arguments(cap, argv=None, variant=None):
        ct.apptools.add_common_arguments(cap, argv=argv, variant=variant)
        if variant is None:
            variant = 'unsupplied'
        ct.apptools.add_output_directory_arguments(cap, variant=variant)
    
    def topbindir(self):
        """ What is the topmost part of the bin directory """
        if "bin" in self.args.bindir:
            return "bin/"
        else:
            return self.args.bindir

    def _outputdir(self, defaultdir, sourcefilename=None):
        """ Used by object_dir and executable_dir.
            defaultdir must be either self.args.objdir or self.args.bindir
        """
        if sourcefilename:
            project_pathname = self._project.pathname(sourcefilename)
            relative = os.path.join(
                defaultdir,
                ct.wrappedos.dirname(project_pathname))
        else:
            relative = defaultdir
        return ct.wrappedos.realpath(relative)

    @memoize
    def object_dir(self, sourcefilename=None):
        """ Put objects into a directory structure that starts with the
            command line objdir but then replicates the project directory
            structure.  This way we can separate object files that have
            the same name but different paths.
        """
        return self._outputdir(self.args.objdir, sourcefilename)

    @memoize
    def object_name(self, sourcefilename):
        """ Return the name (not the path) of the object file
            for the given source.
        """
        name = os.path.split(sourcefilename)[1]
        basename = os.path.splitext(name)[0]
        return "".join([basename, ".o"])

    @memoize
    def object_pathname(self, sourcefilename):
        return "".join([self.object_dir(sourcefilename),
                        "/", self.object_name(sourcefilename)])

    @memoize
    def executable_dir(self, sourcefilename=None):
        """ Put the binaries into a directory structure that starts with the
            command line bindir but then replicates the project directory
            structure.  This way we can separate executable files that have
            the same name but different paths.
        """
        return self._outputdir(self.args.bindir, sourcefilename)

    @memoize
    def executable_name(self, sourcefilename):
        name = os.path.split(sourcefilename)[1]
        return os.path.splitext(name)[0]

    @memoize
    def executable_pathname(self, sourcefilename):
        return "".join([self.executable_dir(sourcefilename),
                        "/",
                        self.executable_name(sourcefilename)])

    @memoize
    def staticlibrary_name(self, sourcefilename=None):
        if sourcefilename is None and self.args.static:
            sourcefilename = self.args.static[0]
        name = os.path.split(sourcefilename)[1]
        return "lib" + os.path.splitext(name)[0] + ".a"

    @memoize
    def staticlibrary_pathname(self, sourcefilename=None):
        """ Put static libraries in the same directory as executables """
        if sourcefilename is None and self.args.static:
            sourcefilename = ct.wrappedos.realpath(self.args.static[0])
        return "".join([self.executable_dir(sourcefilename),
                        "/",
                        self.staticlibrary_name(sourcefilename)])

    @memoize
    def dynamiclibrary_name(self, sourcefilename=None):
        if sourcefilename is None and self.args.dynamic:
            sourcefilename = self.args.dynamic[0]
        name = os.path.split(sourcefilename)[1]
        return "lib" + os.path.splitext(name)[0] + ".so"

    @memoize
    def dynamiclibrary_pathname(self, sourcefilename=None):
        """ Put dynamic libraries in the same directory as executables """
        if sourcefilename is None and self.args.dynamic:
            sourcefilename = ct.wrappedos.realpath(self.args.dynamic[0])
        return "".join([self.executable_dir(sourcefilename),
                        "/",
                        self.dynamiclibrary_name(sourcefilename)])

    def all_executable_pathnames(self):
        """ Use the filenames from the command line to determine the 
            executable names.
        """
        allexes = set()
        if self.args.filename:
            allexes = { self.executable_pathname(ct.wrappedos.realpath(source)) 
                            for source in self.args.filename}
        return allexes

    def all_test_pathnames(self):
        """ Use the test files from the command line to determine the 
            executable names.
        """
        alltests = set() 
        if self.args.tests:
            alltestsexes = { self.executable_pathname(ct.wrappedos.realpath(source)) 
                                for source in self.args.tests}
        return alltests
