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
    # The first Namer may change this.  All others need to be able to read it.
    _using_variant_with_hash_bindir = False

    def __init__(self, args, argv=None, variant=None, exedir=None):
        self.args = args
        self._project = ct.git_utils.Project(args)

        # If the user didn't explicitly tell us what bindir to use the
        # generate a unique one for the args
        if self.args.bindir == 'bin/default':
            Namer._using_variant_with_hash_bindir = True
            vwh = ct.configutils.variant_with_hash(args, argv=argv, variant=variant, exedir=exedir)
            self.args.bindir = "".join(["bin/", vwh])
            self.args.objdir = "".join(["bin/", vwh, "/obj"])

    @staticmethod
    def add_arguments(cap, argv=None, variant=None):
        ct.apptools.add_common_arguments(cap, argv=argv, variant=variant)
        ct.apptools.add_output_directory_arguments(cap, 'default')

    def topbindir(self):
        """ What is the topmost part of the bin directory """
        if self._using_variant_with_hash_bindir:
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
    def staticlibrary_name(self, sourcefilename):
        name = os.path.split(sourcefilename)[1]
        return "lib" + os.path.splitext(name)[0] + ".a"

    @memoize
    def staticlibrary_pathname(self, sourcefilename):
        """ Put static libraries in the same directory as executables """
        return "".join([self.executable_dir(sourcefilename),
                        "/",
                        self.staticlibrary_name(sourcefilename)])

    @memoize
    def dynamiclibrary_name(self, sourcefilename):
        name = os.path.split(sourcefilename)[1]
        return "lib" + os.path.splitext(name)[0] + ".so"

    @memoize
    def dynamiclibrary_pathname(self, sourcefilename):
        """ Put dynamic libraries in the same directory as executables """
        return "".join([self.executable_dir(sourcefilename),
                        "/",
                        self.dynamiclibrary_name(sourcefilename)])

