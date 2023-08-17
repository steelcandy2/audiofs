# Defines an abstract base class for Python classes that implement read-only
# FUSE filesystems that, as part of their implementations, cache generated
# files (or files that are otherwise inconvenient to access directly).
#
# The FUSE filesystem classes are assumed to use the fuse-python API.
#
# Copyright (C) James MacKay 2008
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import os
import os.path
import sys

from fuse import Direntry

import fscommon
from fscommon import debug, report, warn, fs_defaultFileSize, \
    fs_handleNoSuchFile, fs_handleDenyAccess
import utilities as ut


# Constants.

# The FUSE pathname separator.
_fs_sep = os.sep

# The pathname of the directory containing the metadata for the files in an
# fs_AbstractMetadataMergedFilesystem.
_fs_metadataSubdirBasename = ".metadata"
_fs_metadataSubdirPathname = _fs_sep + _fs_metadataSubdirBasename
_fs_relativeMetadataSubdirPathname = _fs_metadataSubdirBasename
_fs_metadataSubdirFullName = _fs_metadataSubdirPathname + _fs_sep

# The names of the direct subdirectories of a filesystem's top metadata
# directory.
fs_filesMetadataSubdirBasename = "files"
fs_filesMetadataSubdirPathname = _fs_metadataSubdirFullName + \
    fs_filesMetadataSubdirBasename
fs_relativeFilesMetadataSubdirPathname = os.path.join(
    _fs_relativeMetadataSubdirPathname, fs_filesMetadataSubdirBasename)

fs_summariesMetadataSubdirBasename = "summaries"
fs_summariesMetadataSubdirPathname = _fs_metadataSubdirFullName + \
    fs_summariesMetadataSubdirBasename
fs_relativeSummariesMetadataSubdirPathname = os.path.join(
    _fs_relativeMetadataSubdirPathname, fs_summariesMetadataSubdirBasename)

# The number of characters to remove from the front of a regular (as opposed
# to a summary) metadata file's pathname in order to get a pathname whose
# "dirname" is that of the file that the metadata's contents are about.
#
# Note: this leaves a path separator at the start of the pathname.
_fs_removeFilesMetadataSubdirLength = len(fs_filesMetadataSubdirPathname)

# Direntry objects for each file and directory in a filesystem's top
# metadata directory.
_fs_topMetadataDirentries = [Direntry(name) for name in \
    [fs_filesMetadataSubdirBasename, fs_summariesMetadataSubdirBasename]]


# The extension that is commonly at the very end of the basename of a
# files metadata file (as opposed to a summary file).
#
# See fs_toFilesMetadataFilename().
_fs_commonMetadataFileExtension = "txt"
_fs_fullCommonMetadataFileExtension = \
    ut.ut_fullExtension(_fs_commonMetadataFileExtension)

# The separator to use between the names and values of tags in metadata
# files that contain tags.
_fs_metadataTagNameValueSeparator = "="


# Widely-used metadata file extensions.

# The extension to use in the basenames of metadata files that contain
# the pathname of the file being described.
fs_pathnameMetadataFileExtension = "pathname"


# Option names.
fs_cacheDirOption = "cache"
fs_realDirOption  = "real"
_fs_noMetadataOption = "nometadata"


# The low and high sizes for an fs_AbstractMergedFilesystem's cache of
# fs_ReadOnlyBeingGeneratedFiles.
_fs_beingGeneratedFileCacheLowSize = 20
_fs_beingGeneratedFileCacheHighSize = 40


# Functions

def fs_addNoMetadataOption(parser):
    """
    Adds the 'nometadata' option to a filesystem's option parser (using its
    add_option() method).
    """
    assert parser is not None
    parser.add_option(mountopt = _fs_noMetadataOption, action = "store_false",
        help = "do not generate metadata")


def fs_findTopMetadataSubdirectoryIn(path):
    """
    Returns the pathname of the topmost metadata subdirectory directly under
    the directory with pathname 'path' if it exists, and returns None
    otherwise.
    """
    assert path is not None
    result = None
    if os.path.ismount(path):
        metaDir = os.path.join(path, _fs_metadataSubdirBasename)
        if os.path.isdir(metaDir):
            result = metaDir
    assert (result is None) or os.path.ismount(path)
    return result

def fs_findFilesMetadataSubdirectoryIn(path):
    """
    Returns the pathname of the files subdirectory of the topmost metadata
    subdirectory directly under the directory with pathname 'path' if it
    exists, and returns None otherwise.
    """
    assert path is not None
    result = fs_findTopMetadataSubdirectoryIn(path)
    if result is not None:
        result = os.path.join(result, fs_filesMetadataSubdirBasename)
    assert (result is None) or os.path.ismount(path)
    return result

def fs_toFilesMetadataPathname(path, ext):
    """
    Returns the pathname of the files (as opposed to summary) metadata file
    that ends with extension 'ext' followed by the common files metadata
    extension, and that describes the file with pathname 'path', or returns
    None if the base metadata directory for the file couldn't be found.

    See _fs_toFilesMetadataPathnameRoot().
    See fs_toFilesMetadataFilename().
    """
    result = _fs_toFilesMetadataPathnameRoot(path)
    if result is not None:
        result = fs_toFilesMetadataFilename(result, ext)
    # 'result' may be None
    return result

def _fs_toFilesMetadataPathnameRoot(path):
    """
    Returns the root pathname for files (as opposed to summary) metadata
    files that describe the file with pathname 'path', or None if the base
    files metadata directory for the file couldn't be found. If it's not None
    the result will be under the files metadata subdirectory of the top
    metadata directory.

    'path' is assumed to be a "real" pathname, and NOT one that looks like an
    abolute pathname but is actually relative to a filesystem's mount point.
    """
    #debug("---> in _fs_toMetadataPathnameRoot(%s)" % path)
    assert path is not None
    assert os.path.isabs(path)
    result = None
    mp = ut.ut_mountPoint(path)
    #debug("    mount point = [%s]" % mp)
    if mp is not None:
        mp = ut.ut_toCanonicalDirectory(mp)
        #debug("    canonical mount point = [%s]" % mp)
        metaDir = os.path.join(mp, _fs_metadataSubdirBasename,
                               fs_filesMetadataSubdirBasename)
        #debug("    metadata dir = [%s]" % metaDir)
        if os.path.isdir(metaDir):
            #debug("    metadata dir is existing dir")
            relPath = path[len(mp):]            # strip off 'mp' prefix
            #debug("    rel. path = [%s]" % relPath)
            assert not os.path.isabs(relPath)   # since 'mp' is canonical
            result = os.path.join(metaDir, relPath)
    # 'result' may be None
    #debug("    result = [%s]" % result)
    assert result is None or \
        (os.path.basename(path) == os.path.basename(result))
    return result

def fs_toFilesMetadataFilename(filename, ext):
    """
    Returns the basename of a files (as opposed to summary) metadata file
    that ends with the extension 'ext' followed by the common metadata
    extension, and that describes a file with basename or pathname
    'filename'. 'ext' is usually a file extension that indicates what type
    of metadata is in the file).
    """
    assert filename is not None
    assert ext is not None
    result = ut.ut_addExtension(ut.ut_addExtension(filename, ext),
                                _fs_fullCommonMetadataFileExtension)
    assert result is not None
    assert len(result) >= len(filename) + len(ext)
    return result


def fs_doesEndWithMetadataExtension(path, ext):
    """
    Returns True iff the pathname or basename 'path' ends with the extension
    'ext' followed by the common metadata file extension.
    """
    assert path is not None
    assert ext is not None
    result = False
    (p, e) = os.path.splitext(path)
    if e == _fs_fullCommonMetadataFileExtension:
        (p, e) = os.path.splitext(p)
        if e == ut.ut_fullExtension(ext):
            result = True
    return result

def _fs_hasCommonMetadataFileExtension(path):
    """
    Returns True iff the pathname 'path' ends with the common metadata
    file extension.
    """
    (p, ext) = os.path.splitext(path)
    result = (ext == _fs_fullCommonMetadataFileExtension)
    return result

def fs_removeMetadataFileExtensions(path):
    """
    Returns 'path' with the common and type-specific metadata file extensions
    removed, iff it has any such extensions.
    """
    assert path is not None
    (result, ext) = os.path.splitext(path)
    assert not ext or ext == _fs_fullCommonMetadataFileExtension
    (result, ext) = os.path.splitext(result)
    assert result is not None
    return result


def fs_tagsMapToMetadataFileContents(m):
    """
    Returns the contents of a metadata file that is to contain the names
    and values of the tags in the map 'm'.
    """
    assert m is not None
    lines = [fs_tagMetadataFileLine(k, v) for (k, v) in m.items()]

    # We don't especially care what order the lines are in, just so long as
    # they're in a consistent order.
    lines.sort()

    result = fs_linesToMetadataFileContents(lines)
    assert result is not None
    return result

def fs_linesToMetadataFileContents(lines):
    """
    Returns the contents of a metadata file that is to contain the lines
    in 'lines', in order.
    """
    assert lines is not None

    # Using a newline instead of os.linesep makes the file's contents the
    # same across platforms. (Do we care that much about that?)
    if lines:
        result = "\n".join(lines) + "\n"
    else:
        result = ""
    assert result is not None
    return result

def fs_tagMetadataFileLine(name, value):
    """
    Returns the contents of a line of a metadata file that contains
    information about a tag named 'name' with value 'value', not
    including a terminating newline.
    """
    assert name is not None
    assert value is not None
    result = "%s%s%s" % (name, _fs_metadataTagNameValueSeparator, value)
    assert result is not None
    return result

def fs_parseMetadataTagFileContents(lines):
    """
    Parses the contents of a metadata file that consists solely of lines
    'lines' that are all tag-value pairs, returning a map from the names
    of the tags to their values. Incorrectly-formatted lines are silently
    ignored.

    If there's more than one line whose tag has a given name then our
    result will map the name to the value in the last line in 'lines' with
    that tag name.
    """
    assert lines is not None
    result = {}
    for line in lines:
        (name, value) = _fs_parseMetadataTagFileLine(line)
        if name is not None:
            assert value is not None
            result[name] = value
    assert result is not None
    return result

def _fs_parseMetadataTagFileLine(line):
    """
    Assuming 'line' is a line from a metadata file that specifies a tag
    name-value pair, parses out and returns the tag's name and value as
    a 2-tuple. Iff 'line' is incorrectly-formatted then both items in the
    returned pair will be None.
    """
    assert line is not None
    sep = _fs_metadataTagNameValueSeparator
    sepIndex = line.find(sep)
    if sepIndex > 0:  # starting with 'sep' is invalid
        name = line[:sepIndex]
        value = line[(sepIndex + len(sep)):]
        result = (name, value)
    else:
        result = (None, None)
    assert len(result) == 2
    assert (result[0] is None) == (result[1] is None)
    return result


# Classes.

class fs_MergedFileStat(fscommon.fs_AbstractReadOnlyExistingFileStat):
    """
    Represents information about a file in an fs_AbstractMergedFilesystem.
    """

    def __init__(self, fs, path):
        """
        Initializes this object to represent information about the file in
        the fs_AbstractMergedFilesystem 'fs' whose pathname is 'path'.

        This method assumes that 'path' is relative to 'fs'' mount point
        (though it starts with a pathname separator).
        """
        #debug("---> in fs_MergedFileStat.__init__(%s, %s)" % (fs, path))
        assert fs is not None
        assert path is not None
        fscommon.fs_AbstractReadOnlyExistingFileStat.__init__(self)
        self._fs_filesystem = fs
        self._fs_path = path
        self._fs_existingFilePathname = None
        assert self._fs_filesystem is not None
        assert self._fs_path is not None

    def _fs_device(self):
        #debug("-2-> in _fs_device()")
        f = self._fs_realFilePathname()
        if f is None:
            # Since we assume that there are no mount points in caches we can
            # just return the device for the cached files directory.
            f = self._fs_filesystem.fs_cachedFilesDirectory()
        result = self._fs_statsFor(f).st_dev
        return result

    def _fs_numberOfLinks(self):
        #debug("-2-> in _fs_numberOfLinks()")
        return 1

    def _fs_size(self):
        #debug("-2-> in _fs_size()")
        result = fs_defaultFileSize()
        f = self._fs_realFilePathname()
        if f is None:
            cached = self._fs_cachedPathname()
            if ut.ut_isExistingRegularFile(cached):
                f = cached
        if f is not None:
            result = self._fs_statsFor(f).st_size
        return result

    def _fs_existingFile(self):
        #debug("---> in fs_MergedFileStat._fs_existingFile()")
        doCacheName = True
        result = self._fs_existingFilePathname
        #debug("    result = '%s' (cached)" % result)
        if result is None:
            result = self._fs_originFilePathname()
            #debug("    result = '%s' (origin file)" % result)
            if result is None:
                cached = self._fs_cachedPathname()
                #debug("    cached pathname = [%s]" % cached)
                if ut.ut_isExistingRegularFile(cached):
                    # We don't cache the pathname of a cached generated file
                    # like this since the file could get removed from the
                    # cache at some point in the future.
                    doCacheName = False
                    result = cached
                    #debug("    result = '%s' (cached file)" % result)
            if result is not None and doCacheName:
                #debug("    caching 'result' as the existing file's pathname")
                self._fs_existingFilePathname = result
        #debug("    file stat: existing file pathname = [%s]" % result)
        # 'result' may be None
        return result

    def _fs_realFilePathname(self):
        """
        See fs_AbstractMergedFilesystem.fs_realFilePathname().
        """
        result = self._fs_filesystem.fs_realFilePathname(self._fs_path)
        # 'result' may be None
        return result

    def _fs_originFilePathname(self):
        """
        See fs_AbstractMergedFilesystem.fs_originFilePathname().
        """
        result = self._fs_filesystem.fs_originFilePathname(self._fs_path)
        # 'result' may be None
        return result

    def _fs_cachedPathname(self):
        """
        See fs_AbstractMergedFilesystem.fs_cachedPathname().
        """
        result = self._fs_filesystem.fs_cachedPathname(self._fs_path)
        assert result is not None
        return result

class fs_SummaryMetadataFileStat(fs_MergedFileStat):
    """
    Represents information about a summary metadata file.
    """

    def __init__(self, fs, path):
        """
        See fs_MergedFileStat.__init__().
        """
        #debug("---> in fs_SummaryMetadataFileStat.__init__()")
        assert fs is not None
        assert path is not None
        fs_MergedFileStat.__init__(self, fs, path)
        self._fs_statMode = ut.ut_regularFileMode(ut.ut_readMask)

    def _fs_mode(self):
        #debug("---> in fs_SummaryMetadataFileStat._fs_mode()")
        return self._fs_statMode

    def _fs_realFilePathname(self):
        # There can't be real summary metadata files: don't allow files under
        # the "real files" directory to be taken to be them.
        # 'result' may be None
        return None

    def _fs_originFilePathname(self):
        # There can't be origin files for summary metadata files.
        # 'result' may be None
        return None

class fs_MetadataFileStat(fscommon.fs_AbstractReadOnlyExistingFileStat):
    """
    Represents information about a metadata file in an
    fs_AbstractMetadataMergedFilesystem.
    """

    def __init__(self, fs, path, origPath):
        """
        Initializes this object to represent information about the metaclass
        file in the fs_AbstractMetadataMergedFilesystem 'fs' whose pathname
        is 'path', and whose contents are metadata about the file in 'fs'
        with pathname 'origPath'.

        This method assumes that both 'path' and 'origPath' are relative to
        the filesystem 'fs'' mount point (though they start with a pathname
        separator).
        """
        assert fs is not None
        assert path is not None
        fscommon.fs_AbstractReadOnlyExistingFileStat.__init__(self)
        # 'origPath' can be None
        # At least currently we don't need 'path'.
        if origPath is not None:
            f = fs.fs_originFilePathname(origPath)
        else:
            f = None
        self._fs_describedFile = f

    def _fs_inodeNumber(self):
        #debug("-3-> in _fs_inodeNumber()")
        return 0  # default value

    def _fs_device(self):
        #debug("-3-> in _fs_device()")
        return 0  # default value

    def _fs_numberOfLinks(self):
        #debug("-3-> in _fs_numberOfLinks()")
        return 1

    def _fs_size(self):
        #debug("-3-> in _fs_size()")
        return 0  # default value

    def _fs_existingFile(self):
        #debug("---> in fs_MetadataFileStat._fs_existingFile()")
        return self._fs_describedFile


class fs_GenerateFileDaemonProcessMixin:
    """
    A mixin class that can be inherited by classes that represent daemon
    processes that generate a file in a merged filesystem.

    Subclasses usually just implement our _fs_generateTemporaryFile() method.
    """

    def __init__(self, tmpPath, finalPath):
        """
        Initializes us with the pathname 'tmpPath' of the file we generate
        while we're generating it, and the pathname 'finalPath' that 'tmpPath'
        will be renamed to if/when it's fully and successfully generated.
        """
        #debug("---> in fs_GenerateFileDaemonProcessMixin.__init__(%s, %s)" % (str(tmpPath), str(finalPath)))
        assert tmpPath is not None
        assert finalPath is not None
        self._fs_tmpPath = tmpPath
        self._fs_finalPath = finalPath

    def _ut_reallyRun(self):
        """
        The method that a subclass' _ut_run() method should call as (usually
        all, but sometimes part of) its implementation.
        """
        #debug("---> in fs_GenerateFileDaemonProcessMixin._ut_reallyRun()")
        tmpPath = self._fs_temporaryFile()
        p = self._fs_finalPath
        try:
            self._fs_generateTemporaryFile(tmpPath)
            #debug("    file SUCCESSFULLY generated")
            # 'p' is the pathname of the generated file.
            assert os.path.lexists(tmpPath)
            #debug("    file [%s] exists" % tmpPath)
            os.rename(tmpPath, p)
            #debug("    renamed '%s' to '%s'" % (tmpPath, p))
            assert os.path.lexists(p)
            #debug("*** file '%s' generated" % p)
        except:
            warn("generating a file in a daemon process failed: %s" % ut.ut_exceptionDescription())
            ut.ut_deleteFileOrDirectory(tmpPath)

    def _fs_generateTemporaryFile(self, path):
        """
        Generates the file with pathname 'path' that, iff we're successful,
        will be renamed to have its final name.

        Note: this method is often implemented in a concrete subclass to call
        the _ut_run() method from the ut_AbstractDaemonProcess subclass that
        it inherits in addition to us.
        """
        assert path is not None
        raise NotImplementedError

    def _fs_temporaryFile(self):
        """
        Returns the pathname of the file that we generate (before it's
        renamed to have its final name).
        """
        result = self._fs_tmpPath
        assert result is not None
        return result

    def _ut_debug(self, msg):
        debug(msg)

class fs_GenerateFileFromCommandDaemonProcess(ut.ut_CommandPipeOutputDaemonProcess,
                                              fs_GenerateFileDaemonProcessMixin):
    """
    Represents a daemon process that generates the contents of a file in a
    merged filesystem by executing a shell command to generate its contents.
    """

    def __init__(self, cmd, rfd, wfd, tmpPath, finalPath, doDebug = False):
        """
        Initializes us with the shell command 'cmd' to execute, the pipe's
        readable and writable file descriptors ('rfd' and 'wfd',
        respectively), the pathname 'tmpPath' of the file we generate while
        we're generating it, and the pathname 'finalPath' that 'tmpPath'
        will be renamed to if/when it's fully and successfully generated.
        """
        #debug("---> in fs_GenerateFileFromCommandDaemonProcess.__init__(%s, %s, %s, %s, %s)" % (cmd, str(rfd), str(wfd), str(tmpPath), str(finalPath)))
        assert cmd
        assert rfd
        assert wfd
        assert tmpPath is not None
        assert finalPath is not None
        finalCmd = "%s | %s" % (cmd, ut.ut_teeShellCommand(tmpPath))
        #debug("    finalCmd = [%s]" % finalCmd)

        # Note: the order of the following '__init__()' calls is EXTREMELY
        # important since ut_CommandPipeOutputDaemonProcess.__init__() causes
        # the daemon process to be forked.
        fs_GenerateFileDaemonProcessMixin.__init__(self, tmpPath, finalPath)
        ut.ut_CommandPipeOutputDaemonProcess. \
            __init__(self, finalCmd, rfd, wfd, doDebug)

    def _ut_run(self):
        #debug("---> in fs_GenerateFileFromCommandDaemonProcess._ut_run()")
        self._ut_reallyRun()

    def _fs_generateTemporaryFile(self, path):
        #debug("---> in fs_GenerateFileFromCommandDaemonProcess._fs_generateTemporaryFile(%s)" % path)
        assert path is not None
        ut.ut_CommandPipeOutputDaemonProcess._ut_run(self)


class fs_AbstractMergedFilesystem(fscommon.fs_AbstractReadOnlyFilesystem):
    """
    An abstract base class for classes that implement read-only FUSE
    filesystems that merge an optional directory of "real" files with
    generated (and cached) files (or at least files that are otherwise
    inconvenient to access directly).

    "Real" files have precedence over the ones that are generated.

    Subclasses usually only need to override our _fs_generateFile() and
    _fs_generateDirectoryEntryNames() methods as well as our various
    _fs_generate*MetadataFile() methods, but they should usually
    override _fs_generatedFileOriginFilePathname().
    """

    def __init__(self, *args, **kw):
        fscommon.fs_AbstractReadOnlyFilesystem.__init__(self, *args, **kw)
        self._fs_beingGeneratedFileCache = \
            ut.ut_LeastRecentlyUsedCache(_fs_beingGeneratedFileCacheLowSize,
                                        _fs_beingGeneratedFileCacheHighSize)

    def fs_processOptions(self, opts):
        fscommon.fs_AbstractReadOnlyFilesystem.fs_processOptions(self, opts)

        val = fscommon.fs_parseRequiredSuboption(opts, fs_cacheDirOption)
        d = ut.ut_expandedAbsolutePathname(val)
        ut.ut_createDirectory(d)
        assert os.path.isdir(d)
        self._fs_cacheDir = d

        val = fscommon.fs_parseOptionalSuboption(opts, fs_realDirOption)
        if val is not None:
            val = ut.ut_expandedAbsolutePathname(val)
        self._fs_realDir = val


    def fs_cachedFilesDirectory(self):
        """
        Returns the absolute pathname of the directory under which the cached
        versions of files are stored.
        """
        result = self._fs_cacheDir
        assert result is not None
        assert os.path.isabs(result)
        return result

    def _fs_cacheDirectory(self):
        """
        Returns the absolute pathname of the directory that is at the top
        of our cache.
        """
        result = self._fs_cacheDir
        assert result is not None
        assert os.path.isabs(result)
        return result

    def fs_realFilesDirectory(self):
        """
        Returns the absolute pathname of the directory under which we look
        for "real" files, or None if we don't look for "real" files.
        """
        result = self._fs_realDir
        # 'result' may be None
        result is None or os.path.isabs(result)
        return result


    # FUSE Methods.

    def _fs_uncachedGetattr(self, path):
        #debug("---> in mergedfs._fs_uncachedGetattr(%s)" % path)
        if self._fs_isExistingFile(path):
            #debug("    the file exists")
            result = fs_MergedFileStat(self, path)
            #debug("    result = %s" % ut.ut_printableStat(result))
        else:
            #debug("    the file doesn't exist")
            result = fs_handleNoSuchFile()
        return result

    def _fs_readlink(self, path):
        #debug("---> in mergedfs._fs_readlink(%s)" % path)
        f = self.fs_finalFilePathname(path)
        if f is None:
            #debug("    no such file")
            result = fs_handleNoSuchFile()
        else:
            #debug("    calling os.readlink(%s)" % path)
            result = os.readlink(f)
            #debug("        result = '%s'" % str(result))
        return result

    def _fs_uncachedReaddir(self, path, offset):
        #debug("---> in mergedfs._fs_uncachedReaddir(%s, %s)" % (path, str(offset)))
        # Merge 'real' files with generated ones, with the real ones
        # hiding generated ones of the same name.
        d = self.fs_realFilesDirectory()
        #debug("    real files dir = [%s]" % d)
        s = set()
        if d is not None:
            d = fscommon.fs_pathnameRelativeTo(d, path)
            #debug("    real files subdir for '%s' = [%s]" % (path, d))
            if os.path.lexists(d):
                #debug("    real files subdir exists ...")
                for f in os.listdir(d):
                    #debug("    found entry named [%s]" % f)
                    s.add(f)
                    yield Direntry(f)
        #debug("    adding generated directory entry names:")
        for f in self._fs_generateDirectoryEntryNames(path):
            #debug("    possibly adding entry [%s]" % f)
            if not f in s:
                # We're not hidden by a 'real' file.
                #debug("        yep, adding entry [%s]" % f)
                yield Direntry(f)

    def _fs_open(self, path, flags, *mode):
        #debug("---> in mergedfs._fs_open(%s, %s, %s)" % (path, str(flags), mode))
        if fscommon.fs_areReadOnlyFlags(flags):
            #debug("    file [%s] allowed to be open()ed ..." % path)
            result = self.fs_openFileForReading(path, flags, mode)
            #debug("    ... result = %s" % str(result))
            if result is None:
                #debug("    file doesn't exist")
                result = fs_handleNoSuchFile()
        else:
            #debug("    disallowing writing since we're read-only")
            result = fs_handleDenyAccess()
        return result

    def _fs_read(self, path, length, offset, fd):
        #debug("---> in mergedfs._fs_read(%s, %i, %i, %s)" % (path, length, offset, repr(fd)))
        result = fd.read(length, offset)
        return result

    def _fs_flush(self, path, fd):
        #debug("---> in mergedfs._fs_flush(%s, %s)" % (path, repr(fd)))
        #debug("     _fs_flush() caller's call stack:\n%s" % ut.ut_callStack())
        pass  # nothing to do since we're a read-only filesystem

    def _fs_release(self, path, flags, fd):
        #debug("---> in mergedfs._fs_release(%s, %i, %s)" % (path, flags, repr(fd)))
        fd.release(flags)

    def _fs_statfs(self):
        #debug("---> in mergedfs._fs_statfs()")
        return os.statvfs(self.fs_cachedFilesDirectory())


    def fs_finalFilePathname(self, path):
        """
        Returns the pathname of the "final" file that corresponds to the one
        in this filesystem with pathname 'path', or returns None if we have
        no file corresponding to 'path'.

        The final file corresponding to one in this filesystem is: the one
        under the root of the "real files" directory if there is one and if
        the file is under it; otherwise it is the file with the pathname
        corresponding to 'path' in our cache, if the file is in it; and
        otherwise it's the file corresponding to 'path' that we generate, if
        we can generate such a file.

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).

        Note: this shouldn't be used for directories, since we want to
        handle those specially (by merging the contents of all of the ones
        found).
        """
        #debug("---> in fs_finalFilePathname(%s)" % path)
        assert path is not None
        result = self.fs_realOrCachedFilePathname(path)
        if result is None:
            (tmpFile, result) = self._fs_createCacheFile(path)
        # 'result' may be None
        return result

    def fs_openFileForReading(self, path, flags, mode):
        """
        Returns an object - usally an fs_AbstractReadOnlyFile subclass -
        that allows the file in this filesystem with pathname 'path' to be
        read, or None if there's no file in this filesystem with that
        pathname.

        See fs_AbstractMergedFilesystem._fs_open().
        """
        #debug("---> in fs_openFileForReading(%s)" % path)
        assert path is not None
        #debug("    'being generated file cache contents:\n%s" % str(self._fs_beingGeneratedFileCache))
        result = self._fs_beingGeneratedFileCache.get(path)
        if result is None:
            #debug("    path NOT found in 'being generated' file cache")
            f = self.fs_realOrCachedFilePathname(path)
            if f is not None:
                #debug("    file is real or already cached")
                result = fscommon.fs_ReadOnlyDelegatingFile(f, flags, *mode)
            else:
                regenFunc = lambda p, s = self: s._fs_createCacheFile(p)
                (tmp, f) = regenFunc(path)
                if tmp is not None:
                    #debug("    'tmp' is not None: generating asynchronously")
                    assert f is not None
                    minSize = self._fs_minimumTemporaryGeneratedFileSize()
                    result = fscommon.fs_ReadOnlyBeingGeneratedFile(path, f,
                                                    tmp, regenFunc, minSize)
                    self._fs_addToBeingGeneratedFileCache(path, result)
                elif f is not None:
                    #debug("    'tmp' None but 'f' not None: generated already")
                    result = fscommon. \
                        fs_ReadOnlyDelegatingFile(f, flags, *mode)
                # otherwise the cache file couldn't be created, and so
                # 'result' will be None
        # 'result' may be None
        return result

    def _fs_minimumTemporaryGeneratedFileSize(self):
        """
        Returns the minimum size (in bytes) that a temporary cached file must
        have before we start to read any data from it.
        """
        #assert result >= 0
        return 0

    def _fs_createCacheFile(self, path, fileContents = None):
        """
        Creates a file in our cache for the file in this filesystem with
        pathname 'path', returning

            - (None, None) if the cache file couldn't be created, or
            - (None, p) where 'p' is the pathname of the created cache
              file, if the file was successfully created synchronously
              (so the file 'p' will exist when we return), or
            - (tmpPath, p) if the file is being created asynchronously,
              where 'tmpPath' is the pathname of the temporary file that
              represents the current state of the file as it's being
              generated and 'p' is the pathname that the cache file being
              created will have once it's finished being generated

        If 'fileContents' is not None then it will be used as the contents
        of the cache file; otherwise the cache file's contents will be
        generated.
        """
        #debug("---> in _fs_createCacheFile(%s)" % path)
        assert path is not None
        # 'fileContents' can be None
        result = (None, None)
        p = self.fs_cachedPathname(path)
        p = ut.ut_removeAnyPathnameSeparatorAtEnd(p)
            # so the os.path.split() call below works properly
        #debug("*** cached pathname of [%s] = [%s]" % (path, p))
        (d, f) = os.path.split(p)
        #debug("    d = [%s], f = [%s]" % (d, f))
        assert len(d) > 0
        tmpPath = None
        try:
            ut.ut_createDirectory(d)  # if it doesn't already exist
            (w, tmpPath) = ut.ut_createTemporaryFile(d, f)
            #debug("    temp file pathname = [%s]" % tmpPath)
            w.close()
            #debug("    closed temp file")
            doRename = False
            if fileContents is not None:
                #debug("    writing specified file contents to temp file")
                try:
                    ut.ut_writeFileLines(tmpPath, [fileContents], nl = '')
                    doRename = True
                except:
                    warn("failed to synchronously write file contents to "
                         "the temporary cache file [%s]" % tmpPath)
            else:
                #debug("    generating temp file (asynchronously?) ...")
                rfd = self._fs_generateRegularOrSummaryMetadataFile(path,
                                                             tmpPath, p)
                #debug("    rfd = %s" % str(rfd))
                if rfd is None:
                    #debug("    temp file generated synchronously")
                    doRename = True
                else:
                    #debug("    temp file generated asynchronously")
                    doRename = False  # it'll be renamed asynchronously
                    result = (tmpPath, p)
                    os.close(rfd)
                        # since we currently don't use it
            if doRename:
                #debug("    file SUCCESSFULLY generated from its contents")
                # 'p' is the pathname of the generated file.
                assert os.path.lexists(tmpPath)
                #debug("    file [%s] exists" % tmpPath)
                os.rename(tmpPath, p)
                #debug("    renamed '%s' to '%s'" % (tmpPath, p))
                assert os.path.lexists(p)
                result = (None, p)
                #debug("*** file '%s' generated" % p)
        except:
            #debug("    generating file failed: %s" % ut.ut_exceptionDescription())
            ut.ut_deleteFileOrDirectory(tmpPath)
            result = (None, None)
        assert result is not None
        assert len(result) == 2
        assert (result[0] is None) or (result[1] is not None)
            # (result[0] is not None) implies (result[1] is not None)
        assert (fileContents is None) or (result[0] is None)
            # (fileContents is not None) implies (result[0] is None)
            # that is, the file is created synchronously if it's contents are
            # specified using 'fileContents'
        return result

    def _fs_addToBeingGeneratedFileCache(self, path, f):
        """
        Adds a mapping from the pathname 'path' to the
        fs_ReadOnlyBeingGeneratedFile 'f' to our cache of such files (iff
        there isn't already a mapping for 'path').
        """
        self._fs_beingGeneratedFileCache.tryToAdd(path, f)


    def _fs_isExistingFile(self, path):
        """
        Returns True iff 'path' is the pathname of a file that exists in
        this filesystem.
        """
        #debug("---> in _fs_isExistingFile(%s)" % path)
        f = self.fs_originFilePathname(path)
        #debug("    origin file pathname = [%s]" % f)
        result = (f is not None)
        #debug("    result = %s" % str(result))
        return result

    def fs_originFilePathname(self, path):
        """
        Returns the pathname of the "origin file" for the file in this
        filesystem with pathname 'path', or returns None if there is no such
        origin file or its pathname cannot be obtained.

        A file 'f' has a given file as its origin file if 'f' represents a
        part of that file, a transformation of that file, or is related to
        that file in such a way that its stats can be used to create 'f''s
        stats (though 'f''s stats won't necessaily be straight copies of the
        file's stats). In some filesystems some or all of the files may not
        have origin files.

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).

        See _fs_generatedFileOriginFilePathname().
        """
        #debug("---> in fs_originFilePathname(%s)" % path)
        result = self.fs_realFilePathname(path)
        #debug("    real file pathname = [%s]" % result)
        if result is None:
            # Note: we never return the cached version of a generated file
            # here since its stats may not be the correct ones.
            #debug("   calling _fs_generatedFileOriginFilePathname(%s)" % path)
            #debug("   self = %s" % self.__class__)
            result = self._fs_generatedFileOriginFilePathname(path)
            #debug("    origin file pathname = [%s]" % result)
        # 'result' may be None
        #debug("    result = [%s]" % result)
        return result

    def fs_realOrCachedFilePathname(self, path):
        """
        Returns the absolute pathname of the "real file" or cached file
        corresponding to the file in this filesystem with pathname 'path', or
        returns None if no such file currently exists.

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).
        """
        assert path is not None
        result = self.fs_realFilePathname(path)
        if result is None:
            # There's no "real" file, so look in our cache.
            p = self.fs_cachedPathname(path)
            if os.path.lexists(p):
                result = p
        assert result is None or os.path.isabs(result)
        assert result is None or os.path.lexists(result)
        return result

    def fs_realFilePathname(self, path):
        """
        Returns the absolute pathname of the "real file" corresponding to
        the file in this filesystem with pathname 'path', or returns None if
        no such file currently exists.

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).
        """
        #debug("---> in fs_realFilePathname(%s)" % path)
        result = None
        d = self.fs_realFilesDirectory()
        #debug("    real files dir = [%s]" % d)
        if d is not None:
            p = fscommon.fs_pathnameRelativeTo(d, path)
            #debug("     'path' relative to real files dir = [%s]" % p)
            if os.path.lexists(p):
                #debug("        ... which exists")
                result = p
        assert result is None or os.path.isabs(result)
        assert result is None or os.path.lexists(result)
        #debug("    result = [%s]" % result)
        return result

    def fs_cachedPathname(self, path):
        """
        Returns the absolute pathname that the cached version of the file
        with pathname 'path' would have if it were in our cache.

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).
        """
        #debug("---> in fs_cachedPathname(%s)" % path)
        assert path is not None

        # We use the realpath() of our mount directory so that the same file
        # doesn't end up in multiple places under our cache directory.
        d = self._fs_realMountDirectory()

        # We use the absolute pathname of 'path' in case we're sharing our
        # cache with another filesystem (or something).
        result = fscommon.fs_pathnameRelativeTo(d, path)
        d = self.fs_cachedFilesDirectory()
        result = fscommon.fs_pathnameRelativeTo(d, result)
        assert result is not None
        assert os.path.isabs(result)
        #debug("    result = [%s]" % result)
        return result

    def _fs_realMountDirectory(self):
        """
        Returns the pathname of our mount directory with any and all symlinks
        in it fully resolved.
        """
        result = self._fs_realMountDir
        assert result is not None
        return result

    def _fs_setMountDirectory(self, path):
        """
        Overrides superclass' version.
        """
        #debug("---> in mergedfs' _fs_setMountDirectory(%s)" % path)
        fscommon.fs_AbstractReadOnlyFilesystem. \
            _fs_setMountDirectory(self, path)
        d = os.path.realpath(path)
        self._fs_realMountDir = d
        #debug("    set real path of mount dir to [%s]" % d)
        assert os.path.isabs(d) == os.path.isabs(path)


    def _fs_createGeneratedDirectory(self, path):
        """
        Creates a directory with pathname 'path' as (part of) a generated
        file.
        """
        # If an empty regular file with pathname 'path' already exists then
        # we assume it's a temporary file we created to "hold" the pathname
        # and delete it.
        #debug("---> in _fs_createGeneratedDirectory(%s)" % path)
        if os.path.isfile(path) and os.path.getsize(path) == 0:
            #debug("   deleting temp regular file first")
            ut.ut_deleteFileOrDirectory(path)
        #debug("    creating the directory")
        ut.ut_createDirectory(path)
        #debug("    directory created")


    def _fs_generateDirectoryEntryNames(self, path):
        """
        Generates the (base) filenames of all of the files (including
        directories, of course) that we will generate in the directory
        corresponding to the one with pathname 'path' in this filesystem.

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).

        Subclasses should always override this method.
        """
        assert path is not None
        raise NotImplementedError

    def _fs_generateRegularOrSummaryMetadataFile(self, path, cachedPath,
                                                 finalCachedPath):
        """
        Generates - synchronously or asynchronously - a file with absolute
        pathname 'cachedPath' that is the cached version of the file with
        pathname 'path' in this filesystem, and then - iff it's generated
        asynchronously - renames 'cachedPath' to 'finalCachedPath'. The
        file in the filesystem is assumed to be either a regular (that is,
        non-metadata) file or a summary metadata file: other types of files
        are generated by other means.

        If the file is successfully generated synchronously then None is
        returned. If it will be generated asynchronously then a readable
        file descriptor will be returned that allows the file's contents to
        be read as they're generated: the caller will be responsible for
        closing the descriptor (using os.close()). Otherwise an exception
        will be raised.

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).

        Note: despite the fact that it is to be generated, 'cachedPath' may
        still already exist when this method is called (in order to properly
        create a temporary file name for it while it's being created, for
        example). It can (and should) be overwritten, however.

        See _fs_generateFile().
        """
        #debug("---> in _fs_generateRegularOrSummaryMetadataFile(%s, %s, %s)" % (path, cachedPath, finalCachedPath))
        if not self._fs_isUnderMetadataDirectory(path):
            #debug("    path NOT under metadata dir")
            result = self._fs_generateFile(path, cachedPath, finalCachedPath)
        else:
            #debug("    path IS under metadata dir")
            if self._fs_isSummaryMetadataFilePathname(path):
                #debug("    generating summary metadata file")
                result = self._fs_generateSummaryMetadataFile(path,
                                                cachedPath, finalCachedPath)
            else:
                warn("can't generate the unknown summary metadata file "
                     "[%s]" % path)
                raise ValueError("Can't generate the summary metadata "
                    "file with pathname [%s] since that's not the "
                    "pathname of a known summary metadata file" % path)
        assert result is not None or os.path.lexists(finalCachedPath)
        return result

    def _fs_generateFile(self, path, cachedPath, finalCachedPath):
        """
        Generates - synchronously or asynchronously - a file with absolute
        pathname 'cachedPath' that is the cached version of the file with
        pathname 'path' in this filesystem, and then - iff it's generated
        asynchronously - renames 'cachedPath' to 'finalCachedPath'.

        If the file is successfully generated synchronously then None is
        returned. If it will be generated asynchronously then a readable
        file descriptor will be returned that allows the file's contents to
        be read as they're generated: the caller will be responsible for
        closing the descriptor (using os.close()). Otherwise an exception
        will be raised.

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).

        Note: despite the fact that it is to be generated, 'cachedPath' may
        still already exist when this method is called (in order to properly
        create a temporary file name for it while it's being created, for
        example). It can (and should) be overwritten, however.

        Subclasses should always override this method.
        """
        assert path is not None
        assert cachedPath is not None
        assert os.path.isabs(cachedPath)
        assert finalCachedPath is not None
        assert os.path.isabs(finalCachedPath)
        raise NotImplementedError
        assert result is not None or os.path.lexists(finalCachedPath)
        #return result

    def _fs_generateSummaryMetadataFile(self, path, cachedPath,
                                        finalCachedPath):
        """
        Generates - synchronously or asynchronously - a file with absolute
        pathname 'cachedPath' that is the cached version of the summary
        metadata file with pathname 'path' for this filesystem, and then -
        iff it's generated asynchronously - renames 'cachedPath' to
        'finalCachedPath'.

        If the file is successfully generated synchronously then None is
        returned. If it will be generated asynchronously then a readable
        file descriptor will be returned that allows the file's contents to
        be read as they're generated: the caller will be responsible for
        closing the descriptor (using os.close()). Otherwise an exception
        will be raised.

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).

        Note: despite the fact that it is to be generated, 'cachedPath' may
        still already exist when this method is called (in order to properly
        create a temporary file name for it while it's being created, for
        example). It can (and should) be overwritten, however.

        Subclasses should always override this method.
        """
        assert path is not None
        assert self._fs_isSummaryMetadataFilePathname(path)
        assert cachedPath is not None
        assert os.path.isabs(cachedPath)
        assert finalCachedPath is not None
        assert os.path.isabs(finalCachedPath)
        raise NotImplementedError
        #assert result is not None or os.path.lexists(finalCachedPath)

    def _fs_generatedFileOriginFilePathname(self, path):
        """
        Returns the pathname of the "origin file" for the file generated for
        the file in this filesystem with pathname 'path', or returns None if
        there is no such origin file or its pathname cannot be obtained.

        If the result we return isn't None then the origin file's type -
        directory, regular file, etc. - must be the same as the generated
        file's type.

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).

        Note: this method should not itself generate any files.

        See fs_originFilePathname().
        """
        #debug("===> in mergedfs._fs_generatedFileOriginFilePathname(%s)" % path)
        assert path is not None
        # 'result' may be None
        raise NotImplementedError


class fs_AbstractMetadataMergedFilesystem(fs_AbstractMergedFilesystem):
    """
    An abstract base class for merged filesystems that also include a
    directory of files that contain metadata about the other files in the
    filesystem.

    The metadata files will all be under the directory whose pathname,
    relative to the filesystem's mount point, is the value of
    '_fs_metadataSubdirPathname'. The optional mount suboption named
    '_fs_noMetadataOption' can be used to prevent the metadata subdirectory
    from being created.
    """

    def fs_processOptions(self, opts):
        #debug("---> in fs_AbstractMetadataMergedFilesystem.fs_processOptions()")
        fs_AbstractMergedFilesystem.fs_processOptions(self, opts)

        val = fscommon.fs_parseOptionalSuboption(opts, _fs_noMetadataOption)
        if val is None:
            val = True  # no 'nometadata' opt => generate metadata
        #debug("    nometadata option value = '%s'" % str(val))
        self._fs_doCreateMetadata = val
        #debug("    creating metadata? %s" % str(self._fs_doCreateMetadata))


    def _fs_isTopMetadataDirectory(self, path):
        """
        Returns True iff 'path' is the pathname, relative to our filesystem's
        mount point, of our top metadata directory.
        """
        assert path is not None
        return path == _fs_metadataSubdirPathname or \
                path == _fs_metadataSubdirFullName

    def _fs_isUnderMetadataDirectory(self, path):
        """
        Returns True iff the pathname 'path' is under the metadata directory
        or is the metadata directory itself (and we generate metadata).

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).
        """
        #debug("---> in _fs_isUnderMetadataDirectory(%s)" % path)
        return self._fs_isUnderSpecifiedMetadataSubdirectory(path,
                                    _fs_metadataSubdirPathname)

    def _fs_isUnderFilesMetadataSubdirectory(self, path):
        """
        Returns True iff the pathname 'path' is under the files subdirectory
        of the top metadata directory or is the files subdirectory itself
        (and we generate metadata).

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).
        """
        #debug("---> in _fs_isUnderFilesMetadataSubdirectory(%s)" % path)
        return self._fs_isUnderSpecifiedMetadataSubdirectory(path,
                                    fs_filesMetadataSubdirPathname)

    def _fs_isUnderSummariesMetadataSubdirectory(self, path):
        """
        Returns True iff the pathname 'path' is under the summaries
        subdirectory of the top metadata directory or is the summaries
        subdirectory itself (and we generate metadata).

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).
        """
        #debug("---> in _fs_isUnderSummariesMetadataSubdirectory(%s)" % path)
        return self._fs_isUnderSpecifiedMetadataSubdirectory(path,
                                    fs_summariesMetadataSubdirPathname)

    def _fs_isUnderSpecifiedMetadataSubdirectory(self, path, subdir):
        """
        Returns True iff the pathname 'path' is under the metadata
        subdirectory whose pathname is 'subdir' or is that subdirectory
        itself (and we generated metadata).

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).
        """
        #debug("---> in _fs_isUnderSpecifiedMetadataSubdirectory(%s, %s)" % (path, subdir))
        result = False
        if self._fs_doCreateMetadata:
            #debug("    are creating metadata")
            #debug("    subdir = [%s]" % subdir)
            if path.startswith(subdir):
                result = \
                    (ut.ut_removePathnamePrefix(path, subdir) is not None)
        #debug("    result = %s" % str(result))
        return result

    def _fs_isSummaryMetadataFilePathname(self, path):
        """
        Returns True iff 'path' is the pathname of a file in the summaries
        metadata directory.
        """
        #debug("---> in _fs_isSummaryMetadataFilePathname(%s)" % path)
        assert path is not None
        raise NotImplementedError

    def _fs_allSummaryMetadataFileDirentries(self):
        """
        Returns a list of Direntry objects that together represent all of
        the files and directories in our summaries metadata directory.
        """
        #assert result is not None
        raise NotImplementedError

    def _fs_metadataFileToDescribedFilePathname(self, path):
        """
        Given the pathname 'path' of the files metadata subdirectory or a
        file or directory under that directory, returns the pathname of the
        corresponding non-metadata file or directory.

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator): if that's the case
        then 'result' will also be relative to our mount point (and start
        with a pathname separator).
        """
        #debug("---> in _fs_metadataFileToDescribedFilePathname(%s)" % path)
        assert path is not None
        assert path.startswith(fs_filesMetadataSubdirPathname)
        result = path[_fs_removeFilesMetadataSubdirLength:]
        #debug("    result = [%s]" % result)
        if not result:
            #debug("    converting the files metadata subdirectory itself")
            result = _fs_sep
        elif _fs_hasCommonMetadataFileExtension(result):
            #debug("    converting a file containing metadata")
            result = fs_removeMetadataFileExtensions(result)
        #debug("    result = [%s]" % result)
        assert result  # not None and not ''
        return result


    def _fs_isExistingFile(self, path):
        # Overrides version from fs_AbstractMergedFilesystem.
        #debug("---> in fs_AbstractMetadataMergedFilesystem._fs_isExistingFile(%s)" % path)
        if not self._fs_isUnderMetadataDirectory(path):
            #debug("    file NOT a metadata file")
            result = fs_AbstractMergedFilesystem._fs_isExistingFile(self,
                                                                    path)
        else:
            #debug("    file IS a metadata file")
            result = False
            if self._fs_isUnderFilesMetadataSubdirectory(path):
                origPath = self._fs_metadataFileToDescribedFilePathname(path)
                if not self._fs_isUnderMetadataDirectory(origPath) and \
                   self._fs_isExistingFile(origPath):
                    # 'origPath' is an existing non-metadata file's pathname.
                    result = self._fs_isExistingMetadataFilePathname(path,
                                                                 origPath)
            elif self._fs_isUnderSummariesMetadataSubdirectory(path):
                result = self._fs_isSummaryMetadataFilePathname(path)
        return result


    # FUSE Methods.

    def _fs_fsdestroy(self):
        #debug("---> in metadata mergedfs._fs_fsdestroy()")
        try:
# TODO: decide whether we care that they're out of date: for now we assume the user can delete the cached metadata files manually if they want them updated !!!
            # Delete any and all cached metadata files, if any: they won't
            # reflect any changes made while we're unmounted.
            #d = self.fs_cachedPathname(_fs_metadataSubdirPathname)
            #if os.path.lexists(d):
            #    ut.ut_deleteTree(d)
            pass
        finally:
            fs_AbstractMergedFilesystem._fs_fsdestroy(self)

    def _fs_unlink(self, path):
        #debug("---> in fs_AbstractMetadataMergedFilesystem._fs_unlink(%s)" % path)
        # Summary metadata file can be deleted (but not the summary metadata
        # subdirectory itself).
        if self._fs_isSummaryMetadataFilePathname(path):
            # When a summary metadata file is deleted it means that its
            # contents should be regenerated the next time they're accessed.
            #
            # We delete it by deleting the corresponding cache file iff it
            # exists. Note that the summary file itself will be "magically"
            # recreated (that is, will still exist (with size 0)).
            f = self.fs_cachedPathname(path)
            ut.ut_tryToDeleteAll(f)
        else:
            fs_AbstractMergedFilesystem._fs_unlink(self, path)

    def _fs_uncachedGetattr(self, path):
        #debug("---> in metadata mergedfs._fs_uncachedGetattr(%s)" % path)
        if not self._fs_isUnderMetadataDirectory(path):
            #debug("    not under metadata dir")
            result = fs_AbstractMergedFilesystem._fs_uncachedGetattr(self,
                                                                     path)
        else:
            #debug("    is under metadata dir")
            if self._fs_isUnderFilesMetadataSubdirectory(path):
                #debug("    is under files metadata subdir")
                origPath = self._fs_metadataFileToDescribedFilePathname(path)
                #debug("    origPath = [%s]" % origPath)
                if self._fs_isExistingFile(origPath) and \
                   self._fs_isExistingMetadataFilePathname(path, origPath):
                    #debug("    'path' is name of existing metadata file")
                    result = fs_MetadataFileStat(self, path, origPath)
                    contents = self._fs_metadataFileContents(path, origPath)
                    if contents is not None:
                        # If we don't specify the correct size then read()ing
                        # the metadata file will get no or truncated data.
                        result = fscommon.fs_ResizedFileStat(result,
                                                             len(contents))
                else:
                    #debug("    unknown files metadata file: %s" % path)
                    result = fs_handleNoSuchFile()
            elif self._fs_isUnderSummariesMetadataSubdirectory(path):
                #debug("    is under summaries metadata dir")
                if path == fs_summariesMetadataSubdirPathname:
                    #debug("    top summaries metadata dir")
                    result = fs_MetadataFileStat(self, path, _fs_sep)
                elif self._fs_isSummaryMetadataFilePathname(path):
                    #debug("    known summary metadata file")
                    result = fs_SummaryMetadataFileStat(self, path)
                else:
                    #debug("    unknown summaries metadata file: %s" % path)
                    result = fs_handleNoSuchFile()
            elif self._fs_isTopMetadataDirectory(path):
                #debug("    is the top metadata dir?")
                if self._fs_doCreateMetadata:
                    #debug("    yes, since metadata dir was created")
                    result = fs_MetadataFileStat(self, path, _fs_sep)
                else:
                    #debug("    no, but maybe it's a 'regular' dir")
                    result = fs_AbstractMergedFilesystem. \
                        _fs_uncachedGetattr(self, path)
            else:
                warn("can't get the attributes of the unknown/unexpected "
                     "metadata file: [%s]" % path)
                result = fs_handleNoSuchFile()
        return result

    def _fs_readlink(self, path):
        #debug("---> in metadata mergedfs._fs_readlink(%s)" % path)
        if not self._fs_isUnderMetadataDirectory(path):
            result = fs_AbstractMergedFilesystem._fs_readlink(self, path)
        else:
            # Metadata files are never symlinks.
            result = fscommon.fs_handleImproperLink(path)
        return result

    def _fs_uncachedReaddir(self, path, offset):
        #debug("---> in metadata mergedfs._fs_uncachedReaddir(%s, %s)" % (path, str(offset)))
        rootDir = _fs_sep
        if not self._fs_isUnderMetadataDirectory(path):
            if path != rootDir:
                for e in fs_AbstractMergedFilesystem. \
                                _fs_uncachedReaddir(self, path, offset):
                    yield e
            else:  # the top-level directory
                msb = _fs_metadataSubdirBasename
                isMetadata = self._fs_doCreateMetadata
                #debug("    isMetadata? %s. metadata subdir = [%s]" % (str(isMetadata), msb))
                if isMetadata:
                    #debug("   adding entry to top dir for metadata subdir [%s]" % msb)
                    yield Direntry(msb)
                for e in fs_AbstractMergedFilesystem. \
                                    _fs_uncachedReaddir(self, path, offset):
                    #debug("   root dir entry name = '%s'" % e.name)
                    if e.name != msb or not isMetadata:
                        yield e
                    else:
                        #debug("    removed a metadata top dir (from the real dir?)")
                        pass
        else:
            if self._fs_isUnderSummariesMetadataSubdirectory(path):
                # Currently 'path' should BE the summaries metadata dir
                for entry in self._fs_allSummaryMetadataFileDirentries():
                    yield entry
            elif self._fs_isUnderFilesMetadataSubdirectory(path):
                origDir = self._fs_metadataFileToDescribedFilePathname(path)
                #debug("    origDir = [%s]" % origDir)
                if not self._fs_isUnderMetadataDirectory(origDir):
                    #debug("    we're not creating metadata for our metadata")
                    if origDir != rootDir:
                        #debug("    not reading the top metadata directory")
                        for e in fs_AbstractMergedFilesystem. \
                                _fs_uncachedReaddir(self, origDir, offset):
                            #debug("        origDir entry's name = '%s'" % e.name)
                            for entry in self. \
                                  _fs_metadataDirentriesFor(origDir, e):
                                yield entry
                    else:
                        #debug("    reading the top metadata directory")
                        for e in fs_AbstractMergedFilesystem. \
                                _fs_uncachedReaddir(self, origDir, offset):
                            # Don't include /.metadata/.metadata
                            if e.name != _fs_metadataSubdirBasename:
                                for entry in self. \
                                      _fs_metadataDirentriesFor(origDir, e):
                                    yield entry
            else:  # is top metadata directory
                assert self._fs_isTopMetadataDirectory(path)
                    # otherwise we've found a new/unexpected metadata dir
                for entry in _fs_topMetadataDirentries:
                    yield entry

    def _fs_access(self, path, mode):
        #debug("---> in metadata mergedfs._fs_access(%s, %s)" % (path, str(mode)))
        assert path is not None
        if self._fs_isUnderMetadataDirectory(path):
            # Allow access to the metadata file iff the described file does
            # or if it's a non-files metadata file or directory.
            if self._fs_isUnderFilesMetadataSubdirectory(path):
                path = self._fs_metadataFileToDescribedFilePathname(path)
            else:  # top metadata dir or summaries dir/file
                path = None
                result = fscommon. \
                    fs_allowEveryoneNonwritingAccess(path, mode)
        if path is not None:
            result = fs_AbstractMergedFilesystem._fs_access(self, path, mode)
        return result

    def _fs_open(self, path, flags, *mode):
        #debug("---> in metadata mergedfs._fs_open(%s, %s, %s)" % (path, str(flags), mode))
        if not self._fs_isUnderMetadataDirectory(path):
            #debug("    opening non-metadata file")
            result = fs_AbstractMergedFilesystem._fs_open(self, path,
                                                          flags, *mode)
        else:
            #debug("    opening metadata file")
            if not fscommon.fs_areReadOnlyFlags(flags):
                result = fs_handleDenyAccess()
            else:
                #debug("    for reading")
                p = self.fs_cachedPathname(path)
                if os.path.lexists(p):  # metadata file is already cached
                    result = fscommon. \
                        fs_ReadOnlyDelegatingFile(p, flags, *mode)
                else:
                    result = self._fs_createCachedMetadataFile(path, p,
                                                                flags, *mode)
                    if result is None:
                        result = fs_handleNoSuchFile()
        #debug("    result = %s" % repr(result))
        return result

    def fs_realOrCachedFilePathname(self, path):
        """
        Overrides fs_AbstractMergedFilesystem's version.

        See fs_openFileForReading().
        """
        assert path is not None
        if not self._fs_isUnderMetadataDirectory(path):
            #debug("    looking for real or cached non-metadata file")
            result = fs_AbstractMergedFilesystem. \
                fs_realOrCachedFilePathname(self, path)
        else:
            #debug("    looking for real or cached metadata file: there are no real metadata files, so we only look for (existing) cached ones")
            result = self.fs_cachedPathname(path)
            if not os.path.lexists(result):
                result = None
        assert result is None or os.path.isabs(result)
        assert result is None or os.path.lexists(result)
        return result

    def _fs_createCachedMetadataFile(self, path, cachedPath, flags, *mode):
        """
        Creates - or starts the process of creating - a file with pathname
        'cachedPath' that is a cached version of the metadata file with
        pathname 'path', returning the fs_*File object that represents it
        if it's successful and None if it isn't.

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).
        """
        assert path is not None
        assert cachedPath is not None
        isFile = True
        if self._fs_isUnderSummariesMetadataSubdirectory(path):
            if self._fs_isSummaryMetadataFilePathname(path):
                contents = None  # will have to be generated
            else:
                warn("can't create the cached version of the unknown "
                     "summary metadata file [%s]" % path)
                isFile = False
        elif self._fs_isUnderFilesMetadataSubdirectory(path):
            origPath = self._fs_metadataFileToDescribedFilePathname(path)
            #debug("    orig. path = [%s]" % origPath)
            contents = self._fs_metadataFileContents(path, origPath)
            assert contents is not None
                # since we're opening a regular file, not a directory
        else:
            warn("can't create the cached version of the metadata file "
                 "[%s] since it isn't a known type of summary metadata "
                 "file (like a files or summary metadata file)" % path)
            isFile = False

        result = None
        if isFile:
            if contents is not None:
                (tmpFile, f) = self._fs_createCacheFile(path, contents)
                if f is None:
                    #debug("    couldn't create the cached version of the metadata file with pathname '%s'" % path)
                    result = None
                else:
                    #debug("    created the cached version of the metadata file with pathname '%s' synchronously" % path)
                    result = fscommon.fs_ReadOnlyDelegatingFile(cachedPath,
                                                                flags, *mode)
            else:
                #debug("    creating the cached version of the metadata file with pathname '%s' asynchronously" % path)
                result = self.fs_openFileForReading(path, flags, mode)
        # 'result' may be None
        return result

    def _fs_pathnameMetadataFileContents(self, path, origPath):
        """
        Returns the contents of the metadata file that contains the
        absolute pathname of the file with pathname 'origPath'.

        This method assumes that both 'path' and 'origPath' are relative to
        our mount point (though they start with a pathname separator).
        """
        #debug("---> in _fs_pathnameMetadataFileContents(%s, %s)" % (path, origPath))
        assert path is not None
        assert origPath is not None
        result = fscommon.fs_pathnameRelativeTo(self.fs_mountDirectory(),
                                                origPath)
        result = fs_linesToMetadataFileContents([result])
        #debug("    result = [%s]" % result)
        assert result is not None
        return result


    def _fs_isExistingMetadataFilePathname(self, path, origPath):
        """
        Returns True iff 'path' is the pathname of a metadata file or
        directory that exists. The metadata file corresponds to the
        non-metadata file with pathname 'origPath', which has already been
        determined to exist.

        This method assumes that 'path' and 'origPath' are relative to our
        mount point (though they both start with a pathname separator).
        """
        assert path is not None
        assert self._fs_isUnderMetadataDirectory(path)
        assert origPath is not None
        assert self._fs_isExistingFile(origPath)
        raise NotImplementedError

    def _fs_metadataFileContents(self, path, origPath):
        """
        Returns a string consisting of the entire contents of the metadata
        file with pathname 'path' that contains metadata describing the file
        with pathname 'origFile', or None if there is no metadata file with
        pathname 'path'.

        This method assumes that both 'path' and 'origPath' are relative to
        our mount point (though they start with a pathname separator).
        """
        assert path is not None
        assert origFile is not None

        # 'result' may be None
        raise NotImplementedError

    def _fs_metadataDirentriesFor(self, origDir, entry):
        """
        Given the Direntry 'entry' that represents a file in the non-metadata
        directory with pathname 'origDir', yields a Direntry for each
        metadata file associated with the file that 'entry' represents. Note
        that 'entry' may represent a directory.

        This method assumes that 'origDir' is relative to our mount point
        (though it starts with a pathname separator).
        """
        assert origDir is not None
        assert entry is not None
        #assert yielded entries are not None
        raise NotImplementedError
