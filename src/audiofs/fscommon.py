#
# $Id: fscommon.py,v 1.47 2013/09/26 13:39:44 jgm Exp $
#
# Defines common functions, constants and classes for use in implementing
# FUSE filesystems using the fuse-python API.
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
import time

import errno
import optparse

import fuse
from fuse import Direntry

import utilities as ut
import config


# Configuration.

if not hasattr(fuse, '__version__'):
    raise RuntimeError, \
        "your fuse-py doesn't know of fuse.__version__, probably it's too old."

fuse.fuse_python_api = (0, 2)

fuse.feature_assert('stateful_files', 'has_init')


# Logging.

def _fs_buildLogFile():
    """
    Builds and returns an open file object on the file to log information to.
    """
    #print "---> in _fs_buildLogFile()"
    name = "logFilePathname"
    path = ut.ut_findAttribute(config.obtain(), name)
    if path is not None:
        #print "   value for path from config is '%s'" % path
        path = ut.ut_expandedAbsolutePathname(path)
        #print "    final value of path is '%s'" % path
        assert path is not None
    else:
        path = os.devnull
        #print "    path set to default value '%s'" % path
    result = file(path, "a", 0)  # append, unbuffered
    assert result is not None
    return result

_fs_logFile = _fs_buildLogFile()
_fs_debugLogFile = ut.ut_findAttribute(config.obtain(), "doDebugLogging")
if _fs_debugLogFile is None:
    _fs_debugLogFile = file(os.devnull, "a")
else:
    #print "debug log file = log file = %s" % _fs_logFile
    _fs_debugLogFile = _fs_logFile

def debug(msg):
    """
    Logs the debugging message 'msg', if we're logging debugging messages.
    """
    #print "---> in debug(%s)" % msg
    print >> _fs_debugLogFile, msg
    _fs_debugLogFile.flush()

def report(msg):
    """
    Logs the message 'msg' as an informational message.
    """
    #print "---> in report(%s)" % msg
    print >> _fs_logFile, msg
    _fs_logFile.flush()

def warn(msg):
    """
    Logs the message 'msg' as a warning message.
    """
    #print "---> in warn(%s)" % msg
    print >> _fs_logFile, "WARNING: " + msg
    _fs_logFile.flush()


def die(msg, ex = None):
    """
    Logs the message 'msg' as a fatal error message and causes this program
    to either exit (if 'ex' is None) or raise the exception 'ex'.
    """
    #print "---> in die(%s, %s)" % (msg, str(ex))
    print >> _fs_logFile, "*** FATAL ERROR: %s" % msg
    try:
        _fs_logFile.close()
    finally:
        if ex is None:
            sys.exit(1)
        else:
            raise ex


# Constants.

# The bitwise ORing of all of the file opening flags that specify how the
# file being opened can be read and/or written.
_fs_allModeFlags = os.O_RDONLY | os.O_WRONLY | os.O_RDWR


# The common part of the usage message for FUSE filesystems.
fs_commonUsage = fuse.Fuse.fusage

# The version of the fuse-python we use.
fs_fuseVersion = fuse.__version__


# The length, in seconds, of a moment.
_fs_moment = 0.25

# The number of times to try to read more bytes from a file that's being
# generated before giving up and assuming that the file's empty.
_fs_numBeingGeneratedReadTries = int(15 / _fs_moment) + 1
    # so that we wait 15 seconds or so at most

# The default file size: for example, the reported size of a file that hasn't
# been generated yet.
#_defaultFileSize = 2 * 1024 * 1024 # 2 megabytes
#_defaultFileSize = 128 * 1024      # 128 kilobytes
_defaultFileSize = 2111000          # a little over 2 megabytes


# Functions.

def fs_defaultFileSize():
    """
    Returns the default file size: for example, the reported size of a file
    that hasn't been generated yet (and thus whose actual size is as yet
    unknown).
    """
    result = _defaultFileSize
    assert result >= 0
    return result

def fs_allowEveryoneNonwritingAccess(path, mode):
    """
    An implementation of a filesystem's _fs_access() method that allows
    access to the file with pathname 'path' according to mode 'mode' iff
    'mode' doesn't include permission to write to the file.

    See fs_AbstractFilesystem._fs_access().
    """
    #debug("---> in fs_allowEveryoneNonwritingAccess(%s, %s)" % (path, str(mode)))
    if mode & os.W_OK:
        #debug("   attempting to write")
        result = fs_handleDenyAccess()
    else:
        #debug("   attempted to ALLOW access by returning True")
        result = 0  # this value apparently allows access
    return result


def fs_areReadOnlyFlags(flags):
    """
    Returns True iff 'flags' indicate that a file is to be opened for
    reading only.

    See fs_handleDenyAccess().
    """
    assert flags is not None
    result = ((flags & _fs_allModeFlags) == os.O_RDONLY)
    return result

def fs_flag2mode(flags):
    """
    Converts the flags 'flags' into a mode string for use in open()ing a
    file in Python.

    From example/xmp.py in the fuse-python distribution.
    """
    md = {os.O_RDONLY: 'r', os.O_WRONLY: 'w', os.O_RDWR: 'w+'}
    result = md[flags & _fs_allModeFlags]
    if flags & os.O_APPEND:
        result = result.replace('w', 'a', 1)
    return result


def fs_parseOptionalSuboption(opts, optName):
    """
    Returns the value of the optional suboption named 'optName' in the
    options 'opts', or returns None if the suboption isn't present in 'opts'.

    Note: 'opts' are options of the type passed as an argument to
    fs_processOptions().
    """
    if hasattr(opts, optName):
        result = getattr(opts, optName)
    else:
        result = None
    # 'result' may be None
    return result

def fs_parseRequiredSuboption(opts, optName):
    """
    Returns the value of the required suboption named 'optName' in the
    options 'opts', or raises an fs_OptionParsingException if the suboption
    isn't present in 'opts'.

    Note: 'opts' are options of the type passed as an argument to
    fs_processOptions().
    """
    result = fs_parseOptionalSuboption(opts, optName)
    if result is None:
        msg = "The required suboption '%s' is missing." % optName
        raise fs_OptionParsingException(msg)
    assert result is not None
    return result


def fs_pathnameRelativeTo(dir, path):
    """
    Returns 'path' relative to the directory with pathname 'dir'.

    This method assumes that 'path' is either a "real" relative pathname
    or is relative to a filesystem's mount point (and thus starts with a
    pathname separator, but is still really a relative pathname).
    """
    assert dir is not None
    assert path is not None
    result = os.path.normpath(dir + os.sep + path)
    assert result is not None
    assert os.path.isabs(result) == os.path.isabs(dir)
    return result


def fs_handleNoSuchFile():
    """
    Handles the case where an attempt is made to access a file that
    doesn't actually exist.
    """
    return -errno.ENOENT

def fs_handleFunctionNotImplemented():
    """
    Handles the case where an attempt is made to call a filesystem
    function that this filesystem doesn't implement.

    Callers should return our result as their result.
    """
    return -errno.ENOSYS

def fs_handleImproperLink(path):
    """
    Handles the case where an attempt is made to manipulate the file with
    pathname 'path' as a symbolic link when it isn't one.

    Callers should return our result as their result.
    """
# TODO: is this a proper use of this error code ???!!!!???
    return -errno.EXDEV

def fs_handleDenyAccess():
    """
    Handles the case where access to a file on this filesystem is denied.

    Callers should return our result as their result.
    """
    return -errno.EACCES

def fs_handleModificationAttempt():
    """
    Handles the case where an attempt is made to modify a read-only
    filesystem or a read-only file in a filesystem.

    Callers should return our result as their result.
    """
    return -errno.EROFS


# Classes.

class fs_Exception(Exception):
    """
    A base class for filsystem-specific classes of exceptions.
    """
    pass

class fs_OptionParsingException(fs_Exception):
    """
    The class of exception raised when parsing a filesystem option or
    suboption fails.
    """

    def __init__(self, msg):
        """
        Initializes an instance with a message describing why parsing the
        option or suboption failed. It should be a complete sentence suitable
        for preceding a filesystem program usage message.
        """
        assert msg is not None
        fs_Exception.__init__(self)
        self._fs_message = msg

    def fs_message(self):
        """
        Returns a message describing why parsing an option or suboption
        failed.
        """
        return self._fs_message


class fs_AbstractReadOnlyFileStat(object):
    """
    An abstract base class for classes that represent the result of the
    stat() call in read-only filesystems.

    Note: do NOT override the _fs_get...() methods since they're "hardwired"
    in the property() calls: instead override the methods that they call.
    """

    def _fs_statsFor(self, path):
        """
        Returns the 'stat' object for the stats of the file with pathname
        'path', or None if the file doesn't exist (including if 'path' is
        None).
        """
        #debug("---> in _fs_statsFor(%s)" % path)
        # 'path' may be None
        result = None
        if path is not None:
            try:
                try:
                    result = os.stat(path)
                    #debug("    got result using 'os.stat()'")
                except OSError:
                    #debug("    OSError occurred: 'path' may be broken symlink")
                    if os.path.islink(path) and not os.path.exists(path):
                        #debug("    'path' is indeed a broken symlink")
                        result = os.lstat(path)
                        #debug("    got result using 'os.lstat()'")
                    else:
                        #debug("    reraised error")
                        raise
            except:
                #debug("    result will be None due to exception: %s" % ut.ut_exceptionDescription())
                assert result == None
        # 'result' may be None
        #debug("    is 'result' None? %s" % str(result is None))
        return result

    def _fs_unsettable(self, newValue):
        """
        Always raises an AttributeError since 'stat' fields can't be
        modified for a file in a read-only filesystem.
        """
        #debug("-0-> in _fs_unsettable(%s)" % newValue)
        raise AttributeError, "can't set file stat information for " + \
            "files in a read-only filesystem"

    def _fs_getMode(self):
        """
        Returns our file's mode.

        See os.stat_result.st_mode.
        """
        #debug("-0-> in _fs_getMode()")
        return self._fs_mode()

    def _fs_getInodeNumber(self):
        """
        Return our file's inode number.

        See os.stat_result.st_inode.
        """
        #debug("-0-> in _fs_getInodeNumber()")
        return self._fs_inodeNumber()

    def _fs_getDevice(self):
        """
        Returns our file's device number.

        See os.stat_result.st_dev.
        """
        #debug("-0-> in _fs_getDevice()")
        return self._fs_device()

    def _fs_getNumberOfLinks(self):
        """
        Return the number of (hard) links to our file.

        See os.stat_result.st_nlink.
        """
        #debug("-0-> in _fs_getNumberOfLinks()")
        return self._fs_numberOfLinks()

    def _fs_getUid(self):
        """
        Returns the UID of the user that own our file.

        See os.stat_result.st_uid.
        """
        #debug("-0-> in _fs_getUid()")
        return self._fs_uid()

    def _fs_getGid(self):
        """
        Returns the GID of the group that owns our file.

        See os.stat_result.st_gid.
        """
        #debug("-0-> in _fs_getGid()")
        return self._fs_gid()

    def _fs_getSize(self):
        """
        Returns the total size of our file in bytes.

        See os.stat_result.st_size.
        """
        #debug("-0-> in _fs_getSize()")
        return self._fs_size()

    def _fs_getLastAccessedTime(self):
        """
        Returns the date/time on which our file was last accessed.

        See os.stat_result.st_atime.
        """
        #debug("-0-> in _fs_getLastAccessedTime()")
        return self._fs_lastAccessedTime()

    def _fs_getLastModifiedTime(self):
        """
        Returns the date/time on which our file was last modified.

        See os.stat_result.st_mtime.
        """
        #debug("-0-> in _fs_getLastModifiedTime()")
        return self._fs_lastModifiedTime()

    def _fs_getCreationTime(self):
        """
        Returns the date/time at which our file was created.

        See os.stat_result.st_ctime.
        """
        #debug("-0-> in _fs_getCreationTime()")
        return self._fs_creationTime()

    st_mode =   property(_fs_getMode, _fs_unsettable)
    st_ino =    property(_fs_getInodeNumber, _fs_unsettable)
    st_dev =    property(_fs_getDevice, _fs_unsettable)
    st_nlink =  property(_fs_getNumberOfLinks, _fs_unsettable)
    st_uid =    property(_fs_getUid, _fs_unsettable)
    st_gid =    property(_fs_getGid, _fs_unsettable)
    st_size =   property(_fs_getSize, _fs_unsettable)
    st_atime =  property(_fs_getLastAccessedTime, _fs_unsettable)
    st_mtime =  property(_fs_getLastModifiedTime, _fs_unsettable)
    st_ctime =  property(_fs_getCreationTime, _fs_unsettable)

    def _fs_mode(self):
        """
        See _fs_getMode().
        """
        #debug("-0-> in _fs_mode()")
        raise NotImplementedError

    def _fs_inodeNumber(self):
        """
        See _fs_getInodeNumber().
        """
        #debug("-0-> in _fs_inodeNumber()")
        raise NotImplementedError

    def _fs_device(self):
        """
        See _fs_getDevice().
        """
        #debug("-0-> in _fs_device()")
        raise NotImplementedError

    def _fs_numberOfLinks(self):
        """
        See _fs_getNumberOfLinks().
        """
        #debug("-0-> in _fs_numberOfLinks()")
        raise NotImplementedError

    def _fs_uid(self):
        """
        See _fs_getUid().
        """
        #debug("-0-> in _fs_uid()")
        raise NotImplementedError

    def _fs_gid(self):
        """
        See _fs_getGid().
        """
        #debug("-0-> in _fs_gid()")
        raise NotImplementedError

    def _fs_size(self):
        """
        See _fs_getSize().
        """
        #debug("-0-> in _fs_size()")
        raise NotImplementedError

    def _fs_lastAccessedTime(self):
        """
        See _fs_getLastAccessedTime().
        """
        #debug("-0-> in _fs_lastAccessedTime()")
        raise NotImplementedError

    def _fs_lastModifiedTime(self):
        """
        See _fs_getLastModifiedTime().
        """
        #debug("-0-> in _fs_lastModifiedTime()")
        raise NotImplementedError

    def _fs_creationTime(self):
        """
        See _fs_getCreationTime().
        """
        #debug("-0-> in _fs_creationTime()")
        raise NotImplementedError

class fs_AbstractReadOnlyExistingFileStat(fs_AbstractReadOnlyFileStat):
    """
    An abstract base class for classes that represent the result of the
    stat() call in read-only filesystems where at least some parts of the
    result are obtained from another existing file.
    """

    def _fs_existingFile(self):
        """
        Returns the pathname of the file that (at least by default) we get
        most of our information from, or None if no such file exists (in
        which case default values will be used).
        """
        # 'result' may be None.
        raise NotImplementedError

    def _fs_statsForExistingFile(self):
        """
        Returns the 'stat' object for the stats of the file whose pathname
        is returned by _fs_existingFile(), or None if the file doesn't
        exist.

        See _fs_statsFor().
        See _fs_existingFile().
        """
        # 'result' may be None
        return self._fs_statsFor(self._fs_existingFile())

    def _fs_statFieldForExistingFile(self, fieldName, defValue):
        """
        Returns the value of the field named 'fieldName' of the 'stat' object
        for the stats of the file whose pathname is returned by
        _fs_existingFile(), or returns 'defValue' if the file doesn't exist.
        """
        #debug("---> in %s._fs_statFieldForExistingFile(%s)" % (type(self).__name__, fieldName))
        stat = self._fs_statsForExistingFile()
        if stat is not None:
            result = getattr(stat, fieldName)
            #debug("    stat field '%s' of existing file = [%s]" % (fieldName, str(result)))
        else:
            result = defValue
            #debug("    stat field '%s' of existing file has the default value [%s]" % (fieldName, str(result)))
        # 'result' may be None
        return result


    def _fs_mode(self):
        #debug("-1-> in fs_AbstractReadOnlyExistingFileStat._fs_mode()")
        result = None  # default value
        stat = self._fs_statsForExistingFile()
        if stat is not None:
            result = stat.st_mode
            #debug("    result = '%o'" % result)
            result = ut.ut_unwritableFileMode(result)
                # since our file's in a read-only filesystem
            #debug("    result = '%o' (unwritable)" % result)
        return result

    def _fs_inodeNumber(self):
        #debug("-1-> in fs_AbstractReadOnlyExistingFileStat._fs_inodeNumber()")
        result = 0  # default value
# I don't think we want to be using another file's inode number here ...
        #result = self._fs_statFieldForExistingFile('st_ino', 0)
        return result

    def _fs_device(self):
        #debug("-1-> in fs_AbstractReadOnlyExistingFileStat._fs_device()")
        result = 0  # default value
# I don't think we want to be using another file's device number here ...
        #result = self._fs_statFieldForExistingFile('st_dev', 0)
        return result

    def _fs_uid(self):
        #debug("-1-> in fs_AbstractReadOnlyExistingFileStat._fs_uid()")
        return self._fs_statFieldForExistingFile('st_uid', 0)

    def _fs_gid(self):
        #debug("-1-> in fs_AbstractReadOnlyExistingFileStat._fs_gid()")
        return self._fs_statFieldForExistingFile('st_gid', 0)

    def _fs_numberOfLinks(self):
        #debug("-1-> in fs_AbstractReadOnlyExistingFileStat._fs_numberOfLinks()")
        return self._fs_statFieldForExistingFile('st_nlink', 1)

    def _fs_size(self):
        #debug("-1-> in fs_AbstractReadOnlyExistingFileStat._fs_size()")
        result = self._fs_statFieldForExistingFile('st_size',
                                                   fs_defaultFileSize())
        #debug("    result = %s" % str(result))
        return result

    def _fs_lastAccessedTime(self):
        #debug("-1-> in fs_AbstractReadOnlyExistingFileStat._fs_lastAccessedTime()")
        return self._fs_statFieldForExistingFile('st_atime', 0)

    def _fs_lastModifiedTime(self):
        #debug("-1-> in fs_AbstractReadOnlyExistingFileStat._fs_lastModifiedTime()")
        return self._fs_statFieldForExistingFile('st_mtime', 0)

    def _fs_creationTime(self):
        #debug("-1-> in fs_AbstractReadOnlyExistingFileStat._fs_creationTime()")
        return self._fs_statFieldForExistingFile('st_ctime', 0)

class fs_DefaultReadOnlyExistingFileStat(fs_AbstractReadOnlyExistingFileStat):
    """
    Represents the result of the stat() call in read-only filesystems where
    the result is obtained from another existing file whose pathname the
    instance was constructed from.
    """

    def __init__(self, path):
        """
        Initializes us from the pathname of the existing file from which we
        get our information.
        """
        assert path is not None
        fs_AbstractReadOnlyExistingFileStat.__init__(self)
        self._fs_path = path

    def _fs_existingFile(self):
        #'result' may be None  # in theory anyway
        return self._fs_path


class fs_ResizedFileStat(object):
    """
    Represents the result of a stat() call that delegates all of its fields
    to another such result except for its file size field.
    """

    def __init__(self, stat, sz):
        """
        Initializes an instance that delegates to 'stat' for everything
        except the file size, which will be 'sz'.
        """
        assert stat is not None
        assert sz >= 0
        object.__init__(self)
        self._fs_delegate = stat
        self._fs_fileSize = sz

    def __getattr__(self, name):
        if name == 'st_size':
            result = self._fs_fileSize
        else:
            result = getattr(self._fs_delegate, name)
        return result


class fs_AbstractReadOnlyFile(object):
    """
    An abstract base class for classes that represent file handles for files
    in a read-only filesystem.
    """

    def __init__(self):
        object.__init__(self)


    # Properties

    def _fs_unsettable(self, newValue):
        """
        Always raises an AttributeError for properties that can't be modified
        directly.
        """
        #debug("---> in _fs_unsettable(%s)" % newValue)
        raise AttributeError, "can't set the value of this property directly"

    def _fs_directIO(self):
        """
        See _fs_doDirectIO().
        """
        return self._fs_doDirectIO()

    def _fs_keepCache(self):
        """
        See _fs_doKeepCache().
        """
        return self._fs_doKeepCache()

    direct_io = property(_fs_directIO, _fs_unsettable)
    keep_cache = property(_fs_keepCache, _fs_unsettable)

    def _fs_doDirectIO(self):
        """
        Returns True if direct I/O is to be used on this file, and False if
        it isn't.
        """
        #debug("---> in fs_AbstractReadOnlyFile._fs_doDirectIO()")
        return False

    def _fs_doKeepCache(self):
        """
        Returns True if the kernel page cache is to be used to cache this
        file, and False if it isn't.
        """
        #debug("---> in fs_AbstractReadOnlyFile._fs_doKeepCache()")
        return True


    # FUSE-esque methods

    def read(self, length, offset):
        """
        Reads and returns the 'length' bytes from our contents starting at
        (0-based) offset 'offset', or as many bytes as we have after that
        offset if it's fewer than 'length'
        """
        raise NotImplementedError

    def release(self, flags = None):
        """
        Releases/closes this file.
        """
        raise NotImplementedError

    def flush(self):
        #debug("---> in fs_AbstractReadOnlyFile.flush()")
        pass  # nothing to do since we're read-only

    def write(self, buf, offset):
        #debug("---> in fs_AbstractReadOnlyFile.write('buf', %i)" % offset)
        return fs_handleModificationAttempt()  # since we're read-only

    def ftruncate(self, length):
        #debug("---> in fs_AbstractReadOnlyFile.ftruncate(%s)" % str(length))
        return fs_handleModificationAttempt()  # since we're read-only

class fs_ReadOnlyDelegatingFile(fs_AbstractReadOnlyFile):
    """
    Represents a (regular) read-only file that delegates its operations to
    another file in a different filesystem.
    """

    def __init__(self, path, flags, *mode):
        """
        Initializes us to delegate to the file with pathname 'path', where
        we're opened with the flags 'flags' and mode 'mode'.

        We assume that 'flags' and 'mode' have already been determined to be
        valid for a read-only file.
        """
        assert path is not None
        fs_AbstractReadOnlyFile.__init__(self)
        self._fs_file = os.fdopen(os.open(path, flags, *mode),
                                  fs_flag2mode(flags))

    def read(self, length, offset):
        #debug("---> in fs_ReadOnlyDelegatingFile.read(%i, %i)" % (length, offset))
        self._fs_file.seek(offset)
        return self._fs_file.read(length)

    def fgetattr(self):
        #debug("---> in fs_ReadOnlyDelegatingFile.fgetattr()")
        return os.stat(self._fs_file)

    def release(self, flags = None):
        self._fs_file.close()

class fs_ReadOnlyStringFile(fs_AbstractReadOnlyFile):
    """
    Represents a (regular) read-only file whose contents are contained
    in a string.

    Note: the getattr() method for a filesystem containing a file represented
    by an instance of this class must be sure to return an object whose
    'st_size' field is exactly the length of the instance's string: otherwise
    when the instance's file is read no or truncated data will be obtained.
    """

    def __init__(self, path, contents, flags, *mode):
        """
        Initializes us to represent a file with pathname 'path' and contents
        'contents'.

        We assume that 'flags' and 'mode' have already been determined to be
        valid for a read-only file.
        """
        #debug("---> in fs_ReadOnlyStringFile.__init__(%s, %s, %s, %s)" % (path, contents, str(flags), str(mode)))
# TODO: check 'flags' and/or 'mode' for validity ???!!!???
# - use fs_areReadOnlyFlags(), but what do we do when it's False ???
        fs_AbstractReadOnlyFile.__init__(self)
        assert path is not None
        assert contents is not None
        self._fs_contents = contents

    # FUSE methods.

    def read(self, length, offset):
        #debug("---> in fs_ReadOnlyStringFile.read(%s, %s)" % (str(length), str(offset)))
        #debug("    contents = [%s]" % self._fs_contents)
        result = self._fs_contents[offset:][:length]
        #debug("    result = [%s]" % result)
        assert result is not None
        return result

    def release(self, flags = None):
        #debug("---> in fs_ReadOnlyStringFile.release(%s)" % str(flags))
        pass  # nothing to do here

class fs_ReadOnlyBeingGeneratedFile(fs_AbstractReadOnlyFile):
    """
    Represents a (regular) read-only file whose contents are (or at least
    fairly recently were) in the process of being generated.
    """

    def __init__(self, path, cachedPath, tmpCachedPath, regenFunc,
                 minTmpFileSize = 0):
        """
        Initializes us to represent a file with pathname 'path' whose
        contents will eventually be in the cached file with pathname
        'cachedPath', but while the contents are still being generated
        they'll be in the temporary file with pathname 'tmpCachedPath'.
        And the one-argument function 'regenFunc' can be used to regenerate
        a cached file from 'path' if our cached file should get removed
        from our cache (usually by aging out).

        While we're reading from 'tmpCachedPath' data read from it won't be
        returned until that file's size is at least 'minTmpFileSize' bytes
        long (or the file's finished being generated).
        """
        #debug("---> in fs_ReadOnlyBeingGeneratedFile.__init__(%s, %s, %s, regenFunc)" % (path, cachedPath, tmpCachedPath))
        fs_AbstractReadOnlyFile.__init__(self)
        assert path is not None
        assert cachedPath is not None
        assert tmpCachedPath is not None
        assert regenFunc is not None
        assert minTmpFileSize >= 0
        self._fs_path = path
        self._fs_cachedPath = cachedPath
        self._fs_tmpCachedPath = tmpCachedPath
        self._fs_regenFunc = regenFunc
        self._fs_minTmpFileSize = minTmpFileSize


    # Properties

    def _fs_doDirectIO(self):
        #debug("---> in fs_ReadOnlyBeingGeneratedFile._fs_doDirectIO()")
        return not os.path.exists(self._fs_cachedPath)

    def _fs_doKeepCache(self):
        """
        Returns True if the kernel page cache is to be used to cache this
        file, and False if it isn't.
        """
        #debug("---> in fs_ReadOnlyBeingGeneratedFile._fs_doKeepCache()")
        return os.path.exists(self._fs_cachedPath)


    # FUSE methods.

    def read(self, length, offset):
        #debug("---> in fs_ReadOnlyBeingGeneratedFile.read(%s, %s)" % (str(length), str(offset)))
        f = None
        try:
            f = self._fs_openFile()
            if f is not None:
                #debug("    found a file to read from: seeking to offset %i" % offset)
                f.seek(offset)
                numTries = _fs_numBeingGeneratedReadTries
                for i in xrange(numTries):
                    #debug("    try #%i: reading at most %i bytes" % (i + 1, length))
                    result = f.read(length)
                    if result:
                        #debug("    actually read %i bytes" % len(result))
                        break  # for
                    else:
                        #debug("    couldn't read any bytes: waiting a moment to try again ...")
                        time.sleep(_fs_moment)
            else:
                warn("no audio file to read() from and couldn't regenerate one")
                result = ""
        finally:
            #debug("    closing the file we read from (if any)")
            ut.ut_tryToCloseAll(f)
        #debug("    *** actually returning result")
        assert result is not None  # though it may be empty
        return result

    def release(self, flags = None):
        #debug("---> in fs_ReadOnlyBeingGeneratedFile.release(%s)" % str(flags))
        #debug("     release() caller's call stack:\n%s" % ut.ut_callStack())
        pass

    def _fs_openFile(self):
        """
        Opens our temporary or cached file, returning a file object if it's
        successful and None if it's not.
        """
        #debug("---> in fs_ReadOnlyBeingGeneratedFile._fs_openFile()")
        #debug("    direct I/O? %s. Keep in cache? %s" % (self.direct_io, self.keep_cache))
        minSize = self._fs_minTmpFileSize
        getSize = ut.ut_fileSize
        maxTries = 3
        #debug("    minSize = %i, maxTries = %i" % (minSize, maxTries))
        result = None
        tries = 1
        while result is None and tries <= maxTries:
            tries += 1
            tmpFile = self._fs_tmpCachedPath
            #debug("    tmpFile = [%s]" % tmpFile)
            if tmpFile is not None:
                while True:
                    assert result is None
                    sz = getSize(tmpFile)
                    #debug("    tmpFile's size is %i bytes" % sz)
                    if sz >= minSize:
                        #debug("    trying to open tmpFile ...")
                        result = self._fs_openForReading(tmpFile)
                        break  # while
                    elif sz < 0:
                        #debug("    tmpFile no longer exists")
                        break  # while
                    else:
                        #debug("    tmpFile too small: waiting briefly ...")
                        time.sleep(_fs_moment)

            if result is None:
                #debug("    tmpFile doesn't exist")
                self._fs_tmpCachedPath = None
                cachedFile = self._fs_cachedPath
                #debug("    cachedFile = [%s]" % cachedFile)
                if cachedFile is not None:
                    #debug("    trying to open cachedFile ...")
                    result = self._fs_openForReading(cachedFile)
                if result is None:
                    warn("cached file doesn't exist: try to regenerate temp and cached file and try again ...")
                    self.fs_regenerate()
        # 'result' may be None
        return result

    def _fs_openForReading(self, p):
        """
        Attempts to open the file with pathname 'p' for reading, returning
        a file object that can be used to read the file if successful, or
        None if the file couldn't be opened because it doesn't exist. An
        OSError will be raised if the file couldn't be opened for some
        other reason.
        """
        #debug("---> in fs_ReadOnlyBeingGeneratedFile._fs_openForReading(%s)" % p)
        assert p is not None
        try:
            #debug("    trying to open '%s' for reading ..." % p)
            result = file(p, "r")
            #debug("    successfully opened '%s' for reading" % p)
        except IOError, ex:
            if ex.errno == errno.ENOENT:
                result = None  # file doesn't exist
            else:
                #debug("    unexpected OSError: %s" % ut.ut_exceptionDescription())
                raise ex
        except:
            #debug("    unexpected type of exception: %s" % ut.ut_exceptionDescription())
            pass
        # 'result' may be None
        return result

    def fs_regenerate(self):
        """
        Regenerates our file's cached file, or raises an appropriate OSError
        if it can't be regenerated.
        """
        (self._fs_tmpCachedPath, cachedPath) = \
            self._fs_regenFunc(self._fs_path)
        if self._fs_tmpCachedPath is None and cachedPath is None:
            raise OSError(errno.ENOENT, "Couldn't regenerate a cached "
                "version of the file '%s'" % self._fs_path)
        elif cachedPath is not None:
            self._fs_cachedPath = cachedPath
        assert self._fs_tmpCachedPath is not None or \
            self._fs_cachedPath is not None

    def fs_cachedPath(self):
        """
        Returns the pathname of the file in which this file's contents will
        eventually be cached.
        """
        result = self._fs_cachedPath
        assert result is not None
        return result

    def fs_temporaryCachedPath(self):
        """
        Returns the pathname of the file that contains this file's contents
        while they're still in the process of being generated, or None if
        that pathname isn't known.
        """
        result = self._fs_tmpCachedPath
        # 'result' may be None
        return result


class _fs_ReadOnlyFilesystemCache(object):
    """
    A cache that caches information used by a filesystem. It assumes that it
    can cache things like file attributes/stats and directory contents
    indefinitely, and so is usually only usable with read-only filesystems.
    """

    def fs_readdir(self, path):
        """
        Returns a list of the results generated by calling 'readdir()' for
        the directory with pathname 'path', or returns None if we contain no
        such results.

        Note: each item in the list is a Direntry or compatible object.
        """
        assert path is not None
        # 'result' may be None
        raise NotImplementedError

    def fs_getattr(self, path):
        """
        Returns the cached result of calling 'getattr()' on the file with
        pathname 'path', or returns None if we contain no such result.
        """
        assert path is not None
        # 'result' may be None
        raise NotImplementedError


    def fs_startReaddir(self, path):
        """
        Called at the start of a filesystem's readdir() call for the
        directory with pathname 'path'.

        See fs_endReaddir(), fs_addReaddirEntry().
        """
        assert path is not None
        raise NotImplementedError

    def fs_addReaddirEntry(self, entry, path, attrs):
        """
        Adds the Direntry (compatible) object 'entry' for the entry with
        pathname 'path' to this cache (if only temporarily). 'attrs' is the
        result of calling 'getattr()' on the entry.

        See fs_startReaddir(), fs_endReaddir().
        """
        assert entry is not None
        assert path is not None
        assert attrs is not None
        raise NotImplementedError

    def fs_endReaddir(self, path):
        """
        Called at the end of a filesystem's readdir() call for the directory
        with pathname 'path', usually in a 'finally' block: it returns the
        list of Direntry (compatible) objects that is the result of the
        readdir() call.

        See fs_startReaddir(), fs_addReaddirEntry().
        """
        assert path is not None
        #assert result is not None
        raise NotImplementedError

class _fs_EmptyReadOnlyFilesystemCache(_fs_ReadOnlyFilesystemCache):
    """
    The class of _fs_ReadOnlyFilesystemCache that is always empty, and hence
    caches nothing.
    """

    def __init__(self):
        #debug("---> in _fs_EmptyReadOnlyFilesystemCache.__init__()")
        self._fs_entries = None

    def fs_readdir(self, path):
        #debug("---> in _fs_EmptyReadOnlyFilesystemCache.fs_readdir(%s)" % path)
        #assert path is not None
        # 'result' may be None
        return None

    def fs_getattr(self, path):
        #debug("---> in _fs_EmptyReadOnlyFilesystemCache.fs_getattr(%s)" % path)
        #assert path is not None
        # 'result' may be None
        return None

    def fs_startReaddir(self, path):
        #debug("---> in _fs_EmptyReadOnlyFilesystemCache.fs_startReaddir(%s)" % path)
        assert path is not None
        self._fs_entries = []

    def fs_addReaddirEntry(self, entry, path, attrs):
        #debug("---> in _fs_EmptyReadOnlyFilesystemCache.fs_addReaddirEntry(%s, %s, %s)" % (str(entry), path, str(attrs)))
        assert entry is not None
        assert path is not None
        assert attrs is not None
        self._fs_entries.append(entry)

    def fs_endReaddir(self, path):
        #debug("---> in _fs_EmptyReadOnlyFilesystemCache.fs_endReaddir(%s)" % path)
        assert path is not None
        result = self._fs_entries
        self._fs_entries = None
        assert result is not None
        return result

class _fs_LargeDirectoryReadOnlyFilesystemCache(_fs_ReadOnlyFilesystemCache):
    """
    The class of _fs_ReadOnlyFilesystemCache that caches information about
    large directories - that is, directories with a large number of entries -
    so that listing and searching them doesn't take an excessively long time.
    """

    def __init__(self, minCacheableSize):
        """
        Initializes us with the minimum number of entries a directory must
        have in order for us to permanently cache information about it.
        """
        #debug("---> in _fs_LargeDirectoryReadOnlyFilesystemCache.__init__(%i)" % minCacheableSize)
        assert minCacheableSize >= 0
        self._fs_minCacheableSize = minCacheableSize
        self._fs_readdirMap = {}
            # a map from the pathname of a directory to a list of Direntry
            # (compatible) objects for each of the directory's entries
        self._fs_getattrMap = {}
            # a map from the pathname of a file to the 'stat' object that
            # contains the file's attributes
        self._fs_tempGetattrMap = {}
            # a map from the pathname of a file in the directory that the
            # current readdir() call is on to the 'stat' object that contains
            # the file's attributes: it will be empty if there's no current
            # readdir() call
        self._fs_tempDirentryList = None
            # a list of Direntry (compatible) objects for each of the files
            # processed as part of the current readdir() call, or None if
            # there's no current readdir() call

    def fs_readdir(self, path):
        #debug("---> in _fs_LargeDirectoryReadOnlyFilesystemCache.fs_readdir(%s)" % path)
        #assert path is not None
        result = self._fs_readdirMap.get(path)
        # 'result' may be None
        return result

    def fs_getattr(self, path):
        #debug("---> in _fs_LargeDirectoryReadOnlyFilesystemCache.fs_getattr(%s)" % path)
        #assert path is not None
        result = self._fs_getattrMap.get(path)
        if result is None:
            result = self._fs_tempGetattrMap.get(path)
        # 'result' may be None
        return result

    def fs_startReaddir(self, path):
        #debug("---> in _fs_LargeDirectoryReadOnlyFilesystemCache.fs_startReaddir(%s)" % path)
        assert path is not None
        assert len(self._fs_tempGetattrMap) == 0
        self._fs_tempDirentryList = []

    def fs_addReaddirEntry(self, entry, path, attrs):
        #debug("---> in _fs_LargeDirectoryReadOnlyFilesystemCache.fs_addReaddirEntry(%s, %s, %s)" % (str(entry), path, str(attrs)))
        assert entry is not None
        assert path is not None
        assert attrs is not None
        self._fs_tempDirentryList.append(entry)
        self._fs_tempGetattrMap[path] = attrs

    def fs_endReaddir(self, path):
        #debug("---> in _fs_LargeDirectoryReadOnlyFilesystemCache.fs_endReaddir(%s)" % path)
        assert path is not None
        result = self._fs_tempDirentryList
        if len(result) >= self._fs_minCacheableSize:
            # The directory readdir() was called on is large enough for us
            # to cache information about the files in it.
            self._fs_readdirMap[path] = result
            self._fs_getattrMap.update(self._fs_tempGetattrMap)
        self._fs_tempDirentryList = None
        self._fs_tempGetattrMap = {}  # not None
        assert result is not None
        return result


class fs_AbstractFilesystem(fuse.Fuse):
    """
    An abstract base class for classes that implement FUSE filesystems.
    """

    def __init__(self, *args, **kw):
        fuse.Fuse.__init__(self, *args, **kw)
        self._fs_mountDir = None  # set in fs_processOptions()

    def fs_start(self, usageMsg):
        """
        Starts up this filesystem upon being mounted.
        """
        #debug("---> in fs_start()")
        opts = optparse.Values()
        self.parse(values = opts, errex = 1)
        areArgsValid = True
        if self.fuse_args.mount_expected():
            try:
                self.fs_processOptions(opts)
            except fs_OptionParsingException, ex:
                areArgsValid = False
                fullMsg = "\n%s%s\n" % (ex.fs_message(), usageMsg)
                print >> sys.stderr, fullMsg
        if areArgsValid:
            self.main()

    def fs_processOptions(self, opts):
        """
        Process our options 'opts' after they've been parsed out of our
        command line arguments, raising an fs_OptionParsingException iff the
        options aren't correct.

        Note: overriding versions of this method should call their
        superclass' version.
        """
        val = None
        if hasattr(opts, 'o'):
            val = opts.o.mountpoint
        if val is None:
            msg = "The filesystem mount point wasn't specified."
            raise fs_OptionParsingException(msg)
        self._fs_setMountDirectory(ut.ut_expandedAbsolutePathname(val))

    def main(self, *a, **kw):
        """
        Causes us to start doing our main processing after having processed
        our options.
        """
        fc = self._fs_fileClass()
        if fc is not None:
            self.file_class = fc
        return fuse.Fuse.main(self, *a, **kw)


    def fs_mountDirectory(self):
        """
        Returns the absolute pathname of the directory that is this
        filesystem's mount point.
        """
        result = self._fs_mountDir
        assert result is not None
        assert os.path.isabs(result)
        return result

    def _fs_setMountDirectory(self, path):
        """
        Sets our mount directory to 'path'.

        Note: this (perhaps obviously) won't change the directory on which
        this filesystem is mounted. Subclasses should always call their
        superclass' version of this method with 'path' as its argument,
        then do whatever other processing that they want (such as setting
        another field's value).

        See fs_mountDirectory()
        """
        assert path is not None
        self._fs_mountDir = path

    def _fs_fileClass(self):
        """
        Returns our the class whose instances are to be used to represent
        individual files in our filesystem, or returns None if the default
        class is to be used.
        """
        return None

    def _fs_handleFuseMethodError(self, methodName):
        """
        Handles an exception being raised by the FUSE filesystem method of
        our named 'methodName'.
        """
        report("*** FILESYSTEM ERROR [%s] ***" % type(self))
        report("FUSE filesystem method named '%s()' failed: %s" %
                (methodName, ut.ut_exceptionDescription()))


    # FUSE Methods.

    def fsinit(self):
        try:
            #debug("---> in fsinit() for fs '%s'" % type(self).__name__)
            return self._fs_fsinit()
        except:
            self._fs_handleFuseMethodError("fsinit")
            raise

    def _fs_fsinit(self):
        """See fsinit()."""
        #debug("---> in fs_AbstractFilesystem's _fs_fsinit()")
        # Note: at this point the command line has been parsed and our
        # corresponding fields set (which is not the case in __init__()).
        pass

    def fsdestroy(self):
        try:
            #debug("---> in fsdestroy() for fs '%s'" % type(self).__name__)
            return self._fs_fsdestroy()
        except:
            self._fs_handleFuseMethodError("fsdestroy")
            raise

    def _fs_fsdestroy(self):
        """See fsdestroy()."""
        #debug("---> in fs_AbstractFilesystem's _fs_fsdestroy()")
        # Try to flush the log file output.
        try:
            os.flush(_fs_logFile)
        except:
            pass
        try:
            os.flush(_fs_debugLogFile)
        except:
            pass

    def unlink(self, path):
        try:
            #debug("---> in unlink(%s) for fs '%s'" % (path, type(self).__name__))
            return self._fs_unlink(path)
        except:
            self._fs_handleFuseMethodError("unlink")
            raise

    def _fs_unlink(self, path):
        """See unlink()."""
        raise NotImplementedError

    def rmdir(self, path):
        try:
            #debug("---> in rmdir(%s) for fs '%s'" % (path, type(self).__name__))
            return self._fs_rmdir(path)
        except:
            self._fs_handleFuseMethodError("rmdir")
            raise

    def _fs_rmdir(self, path):
        """See rmdir()."""
        raise NotImplementedError

    def rename(self, path, path1):
        try:
            #debug("---> in rename(%s, %s) for fs '%s'" % (path, path1, type(self).__name__))
            return self._fs_rename(path, path1)
        except:
            self._fs_handleFuseMethodError("rename")
            raise

    def _fs_rename(self, path, path1):
        """See rename()."""
        raise NotImplementedError

    def chmod(self, path, mode):
        try:
            #debug("---> in chmod(%s, %s) for fs '%s'" % (path, str(mode), type(self).__name__))
            return self._fs_chmod(path, mode)
        except:
            self._fs_handleFuseMethodError("chmod")
            raise

    def _fs_chmod(self, path, mode):
        """See chmod()."""
        raise NotImplementedError

    def chown(self, path, user, group):
        try:
            #debug("---> in chown(%s, %s, %s) for fs '%s'" % (path, str(user), str(group), type(self).__name__))
            return self._fs_chown(path, user, group)
        except:
            self._fs_handleFuseMethodError("chown")
            raise

    def _fs_chown(self, path, user, group):
        """See chown()."""
        raise NotImplementedError

    def truncate(self, path, length):
        try:
            #debug("---> in truncate(%s, %s) for fs '%s'" % (path, str(length), type(self).__name__))
            return self._fs_truncate(path, length)
        except:
            self._fs_handleFuseMethodError("truncate")
            raise

    def _fs_truncate(self, path, length):
        """See truncate()."""
        raise NotImplementedError

    def mknod(self, path, mode, dev):
        try:
            #debug("---> in mknod(%s, %s, %s) for fs '%s'" % (path, str(mode), str(dev), type(self).__name__))
            return self._fs_mknod(path, mode, dev)
        except:
            self._fs_handleFuseMethodError("mknod")
            raise

    def _fs_mknod(self, path, mode, dev):
        """See mknod()."""
        raise NotImplementedError

    def mkdir(self, path, mode):
        try:
            #debug("---> in mkdir(%s, %s) for fs '%s'" % (path, str(mode), type(self).__name__))
            return self._fs_mkdir(path, mode)
        except:
            self._fs_handleFuseMethodError("mkdir")
            raise

    def _fs_mkdir(self, path, mode):
        """See mkdir()."""
        raise NotImplementedError

    def symlink(self, path, path1):
        try:
            #debug("---> in symlink(%s, %s) for fs '%s'" % (path, path1, type(self).__name__))
            return self._fs_symlink(path, path1)
        except:
            self._fs_handleFuseMethodError("symlink")
            raise

    def _fs_symlink(self, path, path1):
        """See symlink()."""
        raise NotImplementedError

    def link(self, path, path1):
        try:
            #debug("---> in link(%s, %s) for fs '%s'" % (path, path1, type(self).__name__))
            return self._fs_link(path, path1)
        except:
            self._fs_handleFuseMethodError("link")
            raise

    def _fs_link(self, path, path1):
        """See link()."""
        raise NotImplementedError

    def write(self, path, buf, offset, fd):
        try:
            #debug("---> in write(%s, buf, %s, %s) for fs '%s'" % (path, str(offset), repr(fd), type(self).__name__))
            return self._fs_write(path, buf, offset, fd)
        except:
            self._fs_handleFuseMethodError("write")
            raise

    def _fs_write(self, path, buf, offset, fd):
        """See write()."""
        raise NotImplementedError

    def fsync(self, isfsyncfile):
        try:
            #debug("---> in fsync(%s) for fs '%s'" % (str(isfsyncfile), type(self).__name__))
            return self._fs_fsync(isfsyncfile)
        except:
            self._fs_handleFuseMethodError("fsync")
            raise

    def _fs_fsync(self, isfsyncfile):
        """See fsync()."""
        raise NotImplementedError

    def utime(self, path, times):
        try:
            #debug("---> in utime(%s, %s) for fs '%s'" % (path, str(times), type(self).__name__))
            return self._fs_utime(path, times)
        except:
            self._fs_handleFuseMethodError("utime")
            raise

    def _fs_utime(self, path, utime):
        """See utime()."""
        raise NotImplementedError


    def statfs(self):
        try:
            #debug("---> in statfs() for fs '%s'" % (path, type(self).__name__))
            return self._fs_statfs()
        except:
            self._fs_handleFuseMethodError("statfs")
            raise

    def _fs_statfs(self):
        """See statfs()."""
        raise NotImplementedError

    def access(self, path, mode):
        try:
            #debug("---> in access(%s, %s) for fs '%s'" % (path, str(mode), type(self).__name__))
            result = self._fs_access(path, mode)
            #debug("   result = %s" % str(result))
            return result
        except:
            self._fs_handleFuseMethodError("access")
            raise

    def _fs_access(self, path, mode):
        """See access()."""
        raise NotImplementedError

    def open(self, path, flags, *mode):
        try:
            #debug("---> in open(%s, %s, %s) for fs '%s'" % (path, str(flags), str(*mode), type(self).__name__))
            return self._fs_open(path, flags, *mode)
        except:
            self._fs_handleFuseMethodError("open")
            raise

    def _fs_open(self, path, flags, *mode):
        """See open()."""
        raise NotImplementedError

    def read(self, path, length, offset, fd):
        try:
            #debug("---> in read(%s, %s, %s, %s) for fs '%s'" % (path, str(length), str(offset), repr(fd), type(self).__name__))
            return self._fs_read(path, length, offset, fd)
        except:
            self._fs_handleFuseMethodError("read")
            raise

    def _fs_read(self, path, length, offset, fd):
        """See read()."""
        raise NotImplementedError

    def flush(self, path, fd):
        try:
            #debug("---> in flush(%s, %s) for fs '%s'" % (path, repr(fd), type(self).__name__))
            return self._fs_flush(path, fd)
        except:
            self._fs_handleFuseMethodError("flush")
            raise

    def _fs_flush(self, path, fd):
        """See flush()."""
        raise NotImplementedError

    def release(self, path, flags, fd):
        try:
            #debug("---> in release(%s, %s, %s) for fs '%s'" % (path, str(flags), repr(fd), type(self).__name__))
            return self._fs_release(path, flags, fd)
        except:
            self._fs_handleFuseMethodError("release")
            raise

    def _fs_release(self, path, flags, fd):
        """See release()."""
        raise NotImplementedError

    def readdir(self, path, offset):
        try:
            #debug("---> in readdir(%s, %s) for fs '%s'" % (path, str(offset), type(self).__name__))
            for de in self._fs_readdir(path, offset):
                if de.name:
                    #debug("    readdir() yielding '%s' ..." % de.name)
                    yield de
                else:
                    raise IOError("readdir() found an entry with an empty name")
        except:
            self._fs_handleFuseMethodError("readdir")
            raise

    def _fs_readdir(self, path, offset):
        """See readdir()."""
        raise NotImplementedError

    def getattr(self, path):
        try:
            #debug("---> in getattr(%s) for fs '%s'" % (path, type(self).__name__))
            return self._fs_getattr(path)
        except:
            self._fs_handleFuseMethodError("getattr")
            raise

    def _fs_getattr(self, path):
        """See getattr()."""
        raise NotImplementedError

    def readlink(self, path):
        try:
            #debug("---> in readlink(%s) for fs '%s'" % (path, type(self).__name__))
            result = self._fs_readlink(path)
            #debug("    result = [%s]" % result)
            return result
        except:
            self._fs_handleFuseMethodError("readlink")
            raise

    def _fs_readlink(self, path):
        """See readlink()."""
        raise NotImplementedError


class fs_MinimalAbstractReadOnlyFilesystem(fs_AbstractFilesystem):
    """
    A minimal abstract base class for classes that implement read-only FUSE
    filesystems.

    This class just implements the FUSE filesystem methods that modify the
    filesystem to return an error code.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes this filesystem.
        """
        #debug("---> in fs_MinimalAbstractReadOnlyFilesystem.__init__()")
        fs_AbstractFilesystem.__init__(self)


    # FUSE Methods.

    def _fs_unlink(self, path):
        #debug("---> in fs_MinimalAbstractReadOnlyFilesystem._fs_unlink(%s)" % path)
        return fs_handleModificationAttempt()

    def _fs_rmdir(self, path):
        #debug("---> in fs_MinimalAbstractReadOnlyFilesystem._fs_rmdir(%s)" % path)
        return fs_handleModificationAttempt()

    def _fs_rename(self, path, path1):
        #debug("---> in fs_MinimalAbstractReadOnlyFilesystem._fs_rename(%s, %s)" %
        #      (path, path1))
        return fs_handleModificationAttempt()

    def _fs_chmod(self, path, mode):
        #debug("---> in fs_MinimalAbstractReadOnlyFilesystem._fs_chmod(%s, %s)" %
        #      (path, str(mode)))
        return fs_handleModificationAttempt()

    def _fs_chown(self, path, user, group):
        #debug("---> in fs_MinimalAbstractReadOnlyFilesystem._fs_chown(%s, %s, %s)" %
        #      (path, str(user), str(group)))
        return fs_handleModificationAttempt()

    def _fs_truncate(self, path, length):
        #debug("---> in fs_MinimalAbstractReadOnlyFilesystem._fs_truncate(%s, %s)" % (path, str(length)))
        return fs_handleModificationAttempt()

    def _fs_mknod(self, path, mode, dev):
        #debug("---> in fs_MinimalAbstractReadOnlyFilesystem._fs_mknod(%s, %s, %s)" %
        #      (path, str(mode), str(dev)))
        return fs_handleModificationAttempt()

    def _fs_mkdir(self, path, mode):
        #debug("---> in fs_MinimalAbstractReadOnlyFilesystem._fs_mkdir(%s, %s)" %
        #      (path, str(mode)))
        return fs_handleModificationAttempt()

    def _fs_symlink(self, path, path1):
        #debug("---> in fs_MinimalAbstractReadOnlyFilesystem._fs_symlink(%s, %s)" %
        #      (path, path1))
        return fs_handleModificationAttempt()

    def _fs_link(self, path, path1):
        #debug("---> in fs_MinimalAbstractReadOnlyFilesystem._fs_link(%s, %s)" %
        #      (path, path1))
        return fs_handleModificationAttempt()

    def _fs_write(self, path, buf, offset, fd):
        #debug("---> in fs_MinimalAbstractReadOnlyFilesystem._fs_write(%s, buf, %s, %s)" % (path, str(offset), repr(fd)))
        return fs_handleModificationAttempt()

    def _fs_fsync(self, isfsyncfile):
        #debug("---> in fs_MinimalAbstractReadOnlyFilesystem._fs_fsync(%s)" % str(isfsyncfile))
        return fs_handleModificationAttempt()

    def _fs_utime(self, path, times):
        #debug("---> in fs_MinimalAbstractReadOnlyFilesystem._fs_utime(%s, %s)" % (path, str(times)))
        # Sets a file's last modified and last accessed date/times.
        return fs_handleModificationAttempt()


class fs_AbstractReadOnlyFilesystem(fs_MinimalAbstractReadOnlyFilesystem):
    """
    An abstract base class for classes that implement read-only FUSE
    filesystems.

    Note: by default anyone will be able to read any file in the filesystem:
    override _fs_access() to change this.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes this filesystem.
        """
        #debug("---> in fs_AbstractReadOnlyFilesystem.__init__()")
        fs_MinimalAbstractReadOnlyFilesystem.__init__(self)
        minSize = kwargs.get("minCacheableDirSize")
        #debug("    minSize = %s" % str(minSize))
        cache = None
        if minSize is not None:
            if ut.ut_isInt(minSize) and minSize >= 0:
                cache = _fs_LargeDirectoryReadOnlyFilesystemCache(minSize)
            else:
                raise ValueError("the value '%s' that was specified as the "
                    "value of the 'minCacheableDirSize' argument to a "
                    "read-only filesystem isn't a non-negative integer")
        if cache is None:
            cache = _fs_EmptyReadOnlyFilesystemCache()
        self._fs_cache = cache


    # FUSE Methods.

    def _fs_readdir(self, path, offset):
        """See readdir()."""
        #debug("---> in fs_AbstractReadOnlyFilesystem._fs_readdir(%s)" % path)
        cache = self._fs_cache
        result = cache.fs_readdir(path)
        if result is None:
            #debug("    result WAS NOT CACHED")
            cache.fs_startReaddir(path)
            try:
                join = os.path.join
                for entry in self._fs_uncachedReaddir(path, offset):
                    p = join(path, entry.name)
                    cache.fs_addReaddirEntry(entry, p,
                                             self._fs_uncachedGetattr(p))
            finally:
                result = cache.fs_endReaddir(path)
        return result

    def _fs_uncachedReaddir(self, path, offset):
        """See _fs_readdir()"""
        raise NotImplementedError

    def _fs_getattr(self, path):
        """See getattr()."""
        #debug("---> in fs_AbstractReadOnlyFilesystem._fs_getattr(%s)" % path)
        result = self._fs_cache.fs_getattr(path)
        if result is None:
            #debug("    result WAS NOT CACHED")
            result = self._fs_uncachedGetattr(path)
        return result

    def _fs_uncachedGetattr(self, path):
        """See _fs_getattr()"""
        raise NotImplementedError

    def _fs_access(self, path, mode):
        #debug("---> in fs_AbstractReadOnlyFilesystem._fs_access(%s, %s)" % (path, str(mode)))
        return fs_allowEveryoneNonwritingAccess(path, mode)
