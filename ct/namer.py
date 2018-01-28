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
        """ This function allows for alternative behaviour to be explore.
            Previously we tried replicating the source directory structure
            to keep object files separated.  The mkdir involved slowed 
            down the build process by about 25%.
        """
        return self.args.objdir

    @memoize
    def object_name(self, sourcefilename):
        """ Return the name (not the path) of the object file
            for the given source.
        """
        directory,name = os.path.split(sourcefilename)
        basename = os.path.splitext(name)[0]
        return "".join([directory.replace('/','@@'),'@@',basename, ".o"])

    @memoize
    def object_pathname(self, sourcefilename):
        return "".join([self.object_dir(sourcefilename),
                        "/", self.object_name(sourcefilename)])

    @memoize
    def executable_dir(self, sourcefilename=None):
        """ Similar to object_dir, this allows for alternative 
            behaviour experimentation.
        """
        return self.args.bindir

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

    def clear_cache(self):
        self.object_dir.cache.clear()
        self.object_name.cache.clear()
        self.object_pathname.cache.clear()
        self.executable_dir.cache.clear()
        self.executable_name.cache.clear()
        self.executable_pathname.cache.clear()
        self.staticlibrary_name.cache.clear()
        self.staticlibrary_pathname.cache.clear()
        self.dynamiclibrary_name.cache.clear()
        self.dynamiclibrary_pathname.cache.clear()

