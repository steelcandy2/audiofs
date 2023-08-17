# Defines a filesystem that caches files up to a maximum collective size
# and/or number.
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

from fscommon import *
import utilities as ut


# Constants.

# The default maximum collective size, in bytes, of all of the
# (non-directory) files in a cache (where a value of 0 means there's no
# maximum collective size).
_fs_defaultCapacityInBytes = 0

# The default maximum number of (non-directory) files in a cache (where a
# value of 0 means there's no maximum number of files).
_fs_defaultMaximumFileCount = 0


# The format of the system command to use to "manually" update a file's
# last accessed time to the current date/time.
_fs_updateAccessTimeCommandFormat = 'touch -a "%s"'


# Option names.
_fs_capacityOption = "capacity"
_fs_maxFileCountOption = "number"
_fs_cacheDirOption = "dir"


# Functions.

def _fs_updateFileAccessTime(path):
    """
    Updates the last accessed time for the file with pathname 'path' to the
    current date/time, returning True iff it is successfully set.
    """
    assert path is not None
    result = True
    try:
        mtime = os.path.getmtime(path)  # keep mtime unchanged
        os.utime(path, (time.time(), mtime))
    except:
        result = False
#    cmd = _fs_updateAccessTimeCommandFormat % path
#    result = (ut.ut_executeShellCommand(cmd) is not None)
    return result

def _fs_compareFilesByAccessTime(path1, path2):
    """
    Compares the files with pathnames 'path1' and 'path2' based on their
    last accessed date/times: returns -1/0/1 iff the file with pathname
    'path1' was last accessed less/equally/more recently than was the file
    with pathname 'path2'.
    """
    # Both 'at1' and 'at2' are (big) floating-point numbers.
    at1 = os.stat(path1).st_atime
    at2 = os.stat(path2).st_atime
    result = cmp(at1, at2)
    assert abs(result) <= 1
    return result


# Classes.

class fs_CachedFile(object):
    """
    Represents a (regular) file in a fs_CachingFilesystem.
    """

    def __init__(self, path, flags, *mode):
        #debug("---> in fs_CachedFile.__init__(%s, %s, %s)" % (path, str(flags), str(mode)))
        object.__init__(self)
        self._fs_file = os.fdopen(os.open(path, flags, *mode),
                                  fs_flag2mode(flags))
        self._fs_path = path
        try:
            sz = os.path.getsize(path)
        except OSError:
            # File 'path' doesn't exist yet.
            sz = 0
        self._fs_startSize = sz
        self._fs_sizeChange = None

    def fs_sizeIncreaseInBytes(self):
        """
        Returns the number of bytes by which the size of our file increased
        during the last time it was open, which may be negative (in which
        case the size of our file decreased), or returns None if the size
        change can't be determined yet (because we've been open()ed without
        being closed/release()d yet).
        """
        return self._fs_sizeChange


    # FUSE methods.

    def read(self, length, offset):
        #debug("---> in fs_CachedFile.read(%i, %i)" % (length, offset))
        self._fs_file.seek(offset)
        return self._fs_file.read(length)

    def write(self, buf, offset):
        #debug("---> in fs_CachedFile.write('buf', %i)" % offset)
        self._fs_file.seek(offset)
        self._fs_file.write(buf)
        return len(buf)

    def flush(self):
        #debug("---> in fs_CachedFile.flush()")
        fd = self._fs_file
        m = fd.mode
        if 'w' in m or 'a' in m:
            fd.flush()

    def fgetattr(self):
        #debug("---> in fs_CachedFile.fgetattr()")
        return os.stat(self._fs_file)

    def ftruncate(self, length):
        #debug("---> in fs_CachedFile.ftruncate(%s)" % str(length))
        self._fs_file.truncate(length)

    def release(self, flags = None):
        #debug("---> in fs_CachedFile.release(%s)" % str(flags))
        self._fs_file.close()
        newSize = os.path.getsize(self._fs_path)
        #debug("    new size = %i" % newSize)
        self._fs_sizeChange = newSize - self._fs_startSize
        #debug("    size change = %i" % self._fs_sizeChange)
        self._fs_startSize = newSize  # in case we're opened again
        #debug("    reset our starting size to %i" % self._fs_startSize)


class fs_CachingFilesystem(fs_AbstractFilesystem):
    """
    Represents filesystems that cache their files: they only keep them until
    their collective size or number reaches a specified limit, then it
    deletes its least recently used files.

    At least currently this class makes several assumptions:
        - cached files are not hard linked to each other (so unlinking a file
          in the cache will actually reduce the collective size of all of the
          files in the cache by the size of the unlinked file)
        - files aren't written to again once they've been copied into our
          cache (though they can be truncated)
            - they can be written, but the change in file size won't be
              detected (at least until the filesystem is remounted) and the
              file won't be marked as having been accessed until it's
              close()d
    """

    def __init__(self, *args, **kw):
        fs_AbstractFilesystem.__init__(self, *args, **kw)
        self._fs_fileSet = set()
        self._fs_totalSizeInBytes = 0

    def fs_processOptions(self, opts):
        #debug("---> in cachefs' fs_processOptions(%s)" % repr(opts))
        fs_AbstractFilesystem.fs_processOptions(self, opts)

        val = fs_parseRequiredSuboption(opts, _fs_cacheDirOption)
        self._fs_actualFilesDir = ut.ut_expandedAbsolutePathname(val)
        #debug("    actual files dir = [%s]" % self._fs_actualFilesDir)

        val = fs_parseOptionalSuboption(opts, _fs_capacityOption)
        if val is None:
            val = _fs_defaultCapacityInBytes
            assert val >= 0
        else:
            val = ut.ut_parseSpaceIntoBytes(val)
            if val is None:
                msg = "'%s' is not a valid cache capacity value." % val
                raise fs_OptionParsingException(msg)
        #debug("    capacity = %s bytes" % str(val))
        self._fs_capacityInBytes = val
        assert self._fs_capacityInBytes >= 0

        val = fs_parseOptionalSuboption(opts, _fs_maxFileCountOption)
        if val is None:
            val = _fs_defaultMaximumFileCount
            assert val >= 0
        else:
            try:
                val = int(val)
            except ValueError:
                msg = "'%s' is not a valid maximum number of files." % val
                raise fs_OptionParsingException(msg)
            if val < 0:
                msg = "The maximum number of cached files '%s' can't be " \
                      "negative" % val
                raise fs_OptionParsingException(msg)
        self._fs_maxFileCount = val
        #debug("    max. file count = %s" % str(self._fs_maxFileCount))
        assert self._fs_maxFileCount >= 0

    def _fs_reconstructFromCacheContents(self):
        """
        Reconstructs our information about our cache from the contents of our
        cache directory.
        """
        #debug("---> in _fs_reconstructFromCacheContents()")
        totalSize = 0
        fileSet = set()
        #debug("    total size = %i" % totalSize)
        top = self._fs_actualFilesDir
        assert top is not None
        for dir, dirnames, filenames in os.walk(top):
            for fname in filenames:
                # Note: we do NOT want to mark these files as having just
                # been accessed.
                f = os.path.join(dir, fname)
                fileSet.add(f)
                totalSize += os.path.getsize(f)
                #debug("    + file '%s': new total size = %i" % (f, totalSize))
        self._fs_totalSizeInBytes = totalSize
        self._fs_fileSet = fileSet
        #debug("    unadjusted: total size = %i, file count = %i" % (self._fs_totalSizeInBytes, len(self._fs_fileSet)))
        self._fs_adjustCache()
        #debug("    adjusted: total size = %i, file count = %i" % (self._fs_totalSizeInBytes, len(self._fs_fileSet)))
        #debug("    file set = [%s]" % ", ".join(self._fs_fileSet))
        assert self._fs_fileSet is not None
        assert self._fs_totalSizeInBytes >= 0
        assert self._fs_isCacheProperlyAdjusted()


    def _fs_actualFile(self, path):
        """
        Returns the pathname of the actual file that backs the file in
        this filesystem with pathname 'path'.

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).
        """
        #debug("---> in _fs_actualFile(%s)" % path)
        assert path is not None
        result = os.path.normpath(self._fs_actualFilesDir + os.sep + path)
        #debug("    result = [%s]" % result)
        assert result is not None
        assert os.path.isabs(result)  # since _fs_actualFilesDir is
        return result

    def _fs_markActualFileAccessed(self, path):
        """
        Marks the actual cache file with pathname 'path' as having just been
        accessed, iff the file exists.

        Note: 'path' is an actual pathname, and NOT one that is relative to
        our mount point.
        """
        #debug("---> in _fs_markActualFileAccessed(%s)" % path)
        assert path is not None
        if os.path.lexists(path):
            #debug("    the file exists: updating its access time")
            _fs_updateFileAccessTime(path)


    def _fs_isCacheProperlyAdjusted(self):
        """
        Returns True iff our cache is properly adjusted: that is, iff it
        doesn't have too many files or files whose collective size exceeds
        its maximum allowed capacity.
        """
        result = not self._fs_areExceedingCapacity() and \
                    (self._fs_excessNumberOfFiles() == 0)
        return result

    def _fs_adjustCache(self):
        """
        Removes the least recently accessed files from our cache until both
        our total file count is no longer above our maximum file count (if we
        have one) and the collective size of all of our files is no longer
        above our maximum allowed capacity.
        """
        #debug("---> in _fs_adjustCache()")
        #self._fs_checkCacheMetadata()
        numExcess = self._fs_excessNumberOfFiles()
        isOverCap = self._fs_areExceedingCapacity()
        #debug("    num. excess files = %i; is over capacity? %s" % (numExcess, str(isOverCap)))
        if numExcess > 0 or isOverCap:
            try:
                orderedFiles = list(self._fs_fileSet)
                orderedFiles.sort(_fs_compareFilesByAccessTime)
                if numExcess > 0:
                    for i in xrange(numExcess):
                        self._fs_deleteFirstFile(orderedFiles)
                    assert self._fs_excessNumberOfFiles() == 0
                    if isOverCap:
                        # It may have changed after deleting the excess files.
                        isOverCap = self._fs_areExceedingCapacity()
                while isOverCap:
                    # Delete files until we're no longer over capacity.
                    self._fs_deleteFirstFile(orderedFiles)
                    isOverCap = self._fs_areExceedingCapacity()
            finally:
                self._fs_fileSet = set(orderedFiles)
        assert self._fs_isCacheProperlyAdjusted()
        #self._fs_checkCacheMetadata()

    def _fs_deleteFirstFile(self, lst):
        """
        Deletes the first file in 'lst', both from our cache and from 'lst'.

        Note: 'path' is the actual pathname of a file in our cache: it isn't
        relative to our mount point.
        """
        #debug("---> in _fs_deleteOneCachedFile()")
        assert lst is not None
        assert len(lst) > 0
        f = lst[0]
        assert os.path.lexists(f)
            # since otherwise unlink() would have already removed it from
            # our file list
        sz = os.path.getsize(f)
        #debug("    file [%s] is %i bytes long" % (f, sz))
        os.remove(f)
        #debug("    deleted the file")
        self._fs_totalSizeInBytes -= sz
        #debug("    decreased our total size to %i" % self._fs_totalSizeInBytes)
        del lst[0]
        #debug("    removed the file from our file list")
        assert self._fs_totalSizeInBytes >= 0
        #assert "self._fs_totalSizeInBytes <= old self._fs_totalSizeInBytes"

    def _fs_checkCacheMetadata(self):
        """
        Checks that our metadata about our cache is in sync with the actual
        contents of the cache.
        """
        isValid = True
        #debug("---> in _fs_checkCacheMetadata()")
        top = self._fs_actualFilesDir
        #debug("    top = '%s'" % top)
        sz = 0
        count = 0
        for dir, dirnames, filenames in os.walk(top):
            for fname in filenames:
                f = os.path.join(dir, fname)
                #debug("    adding '%s'" % f)
                sz += os.path.getsize(f)
                count += 1
        #debug("    our size = %i, calculated size = %i" % (self._fs_totalSizeInBytes, sz))
        ourSize = self._fs_totalSizeInBytes
        if ourSize != sz:
            report("*** TOTAL CACHE SIZE INCORRECT ***")
            report("our total:    %i bytes" % ourSize)
            report("actual total: %i bytes" % sz)
            isValid = False
        ourCount = len(self._fs_fileSet)
        if ourCount != count:
            report("*** NUMBER OF FILES IN CACHE INCORRECT ***")
            report("our count:    %i files" % ourCount)
            report("actual count: %i files" % count)
            report("file set = [%s]" % ", ".join(self._fs_fileSet))
            isValid = False
        if not isValid:
            die("*** CACHE METADATA INCONSISTENT ***")

    def _fs_fileCount(self):
        """
        Returns the number of (non-directory) files that are currently in our
        cache.
        """
        result = len(self._fs_fileSet)
        assert result >= 0
        return result

    def _fs_excessNumberOfFiles(self):
        """
        Returns the number by which we currently exceed the maximum number
        of files that are allowed in our cache.
        """
        #debug("---> in _fs_excessNumberOfFiles()")
        maxNum = self._fs_maxFileCount
        #debug("    max. # allowed = %s" % str(maxNum))
        result = 0
        if maxNum > 0:
            result = max(self._fs_fileCount() - maxNum, 0)
        #debug("    result = %s" % str(result))
        assert result >= 0
        assert result <= self._fs_fileCount()
        assert result == 0 or result < self._fs_fileCount()
        return result

    def _fs_areExceedingCapacity(self):
        """
        Returns true iff the collective size of all of the files in our cache
        exceeds our maximum capacity.
        """
        result = False
        cap = self._fs_capacityInBytes
        if cap > 0:
            result = (self._fs_totalSizeInBytes > cap)
        return result


    # FUSE methods.

    def _fs_fsinit(self):
        #debug("---> in cachefs._fs_fsinit()")
        fs_AbstractFilesystem.fsinit(self)
        self._fs_reconstructFromCacheContents()

    def _fs_statfs(self):
        return os.statvfs(self._fs_actualFilesDir)


    def _fs_mknod(self, path, mode, dev):
        #debug("---> in cachefs._fs_mknod(%s, %s, %s)" % (path, str(mode), str(dev)))
        os.mknod(self._fs_actualFile(path), mode, dev)

    def _fs_mkdir(self, path, mode):
        #debug("---> in cachefs._fs_mkdir(%s, %s)" % (path, str(mode)))
        os.mkdir(self._fs_actualFile(path), mode)

    def _fs_symlink(self, path, path1):
        #debug("---> in cachefs._fs_symlink(%s, %s)" % (path, path1))
        # This isn't implemented because we don't want symlinks into our
        # files (since they can disappear at any time).
        return fs_handleFunctionNotImplemented()

    def _fs_link(self, path, path1):
        #debug("---> in cachefs._fs_link(%s, %s)" % (path, path1))
        # This isn't implemented because we don't want hard links between
        # files in our cache (so that when we delete a file from our cache
        # we can assume that the collective size of all of the files in the
        # cache has decreased by the size of the removed file).
        return fs_handleFunctionNotImplemented()


    def _fs_access(self, path, mode):
        #debug("---> in cachefs._fs_access(%s, %s)" % (path, str(mode)))
        # We don't consider this a file access.
        if not os.access(self._fs_actualFile(path), mode):
            return fs_handleDenyAccess()

    def _fs_open(self, path, flags, *mode):
        #debug("---> in cachefs._fs_open(%s, %s, %s)" % (path, str(flags), mode))
        f = self._fs_actualFile(path)
        self._fs_markActualFileAccessed(f)
        return fs_CachedFile(f, flags, *mode)

    def _fs_read(self, path, length, offset, fd):
        #debug("---> in cachefs._fs_read(%s, %s, %s, %s)" % (path, str(length), str(offset), repr(fd)))
        return fd.read(length, offset)

    def _fs_write(self, path, buf, offset, fd):
        #debug("---> in cachefs._fs_write(%s, 'buf', %s, %s)" % (path, str(offset), repr(fd)))
        return fd.write(buf, offset)

    def _fs_flush(self, path, fd):
        #debug("---> in cachefs._fs_flush(%s, %s)" % (path, repr(fd)))
        # We don't consider this a file access.
        fd.flush()

    def _fs_release(self, path, flags, fd):
        #debug("---> in cachefs._fs_release(%s, %i, %s)" % (path, flags, repr(fd)))
        fd.release(flags)
        f = self._fs_actualFile(path)
        self._fs_markActualFileAccessed(f)
        incr = fd.fs_sizeIncreaseInBytes()
        self._fs_fileSet.add(f)  # may already be in there
        self._fs_totalSizeInBytes += incr
        if incr > 0:
            # No need to adjust the cache if our total size stayed the same
            # or decreased.
            self._fs_adjustCache()

    def _fs_readdir(self, path, offset):
        #debug("---> in cachefs._fs_readdir(%s, %s)" % (path, str(offset)))
        d = self._fs_actualFile(path)
        for f in os.listdir(d):
            yield Direntry(f)


    def _fs_truncate(self, path, length):
        #debug("---> in cachefs._fs_truncate(%s, %s)" % (path, str(length)))
        f = self._fs_actualFile(path)
        sz = os.path.getsize(f)
        if length < sz:
            diff = sz - length
            fd = open(f, "a")
            fd.truncate(length)
            fd.release()
            self._fs_totalSizeInBytes -= diff
        self._fs_markActualFileAccessed(f)
        assert self._fs_totalSizeInBytes >= 0

    def _fs_rename(self, path, path1):
# TODO: we're assuming that both 'path' and 'path1' are in our filesystem -
# is that true ???!!!!???
# - if it wasn't you'd think it would do a copy and delete instead ...
        #debug("---> in cachefs._fs_rename(%s, %s)" % (path, path1))
        f = self._fs_actualFile(path)
        f1 = self._fs_actualFile(path1)
        os.rename(f, f1)

        # Our total cache size doesn't change, but we have to remove 'path'
        # from our set of files and add 'path1' to it.
        if not os.path.isdir(f1):
            # Only non-directory files are in the file set.
            s = self._fs_fileSet
            s.remove(f)
            s.add(f1)
            self._fs_markActualFileAccessed(f1)

    def _fs_chmod(self, path, mode):
        #debug("---> in cachefs._fs_chmod(%s, %s)" % (path, str(mode)))
        # We don't consider this a file access.
        os.chmod(self._fs_actualFile(path), mode)

    def _fs_chown(self, path, user, group):
        #debug("---> in cachefs._fs_chown(%s, %s, %s)" % (path, str(user), str(group)))
        # We don't consider this a file access.
        os.chown(self._fs_actualFile(path), user, group)

    def _fs_fsync(self, isfsyncfile):
        #debug("---> in cachefs._fs_fsync(%s)" % str(isfsyncfile))
        return fs_handleFunctionNotImplemented()

    def _fs_getattr(self, path):
        # We don't consider this a file access.
        return os.lstat(self._fs_actualFile(path))

    def _fs_readlink(self, path):
        #debug("---> in cachefs._fs_readlink(%s)" % path)
        # We don't consider this a file access.
        return os.readlink(self._fs_actualFile(path))

    def _fs_utime(self, path, times):
        #debug("---> in cachefs._fs_utime(%s, %s)" % (path, times))
        # Note that changing a file's access time via this method will affect
        # how long the file stays cached.
        f = self._fs_actualFile(path)
        os.utime(f, times)
        self._fs_markActualFileAccessed(f)
            # which may reset the access time that was just set

    def _fs_unlink(self, path):
        #debug("---> in cachefs._fs_unlink(%s)" % path)
        f = self._fs_actualFile(path)
        sz = os.path.getsize(f)
        #debug("    deleting the file itself")
        os.remove(f)
        #debug("    removing the file from our file list")
        #debug("    file set = [%s]" % ", ".join(self._fs_fileSet))
        self._fs_fileSet.remove(f)
        #debug("    decreasing our total size by %i bytes" % sz)
        self._fs_totalSizeInBytes -= sz
        #debug("    our total size now = %i bytes" % self._fs_totalSizeInBytes)
        assert self._fs_totalSizeInBytes >= 0

    def _fs_rmdir(self, path):
        #debug("---> in cachefs._fs_rmdir(%s)" % path)
        # We don't cache directories, so our fields don't need to be updated.
        d = self._fs_actualFile(path)
        assert os.path.isdir(d)
        os.rmdir(d)


# Main method.

def main():
    """
    Main method.
    """
    # cachefs -o dir=PATH [capacity=SIZE] [number=NUM] mountpoint
    usage = """

A filesystem that caches its files by storing them under (a subdirectory of)
'dir' until either the files' collective size (not including directories)
exceeds 'capacity' or the number of files exceeds 'number'. At least one of
'capacity' or 'number' must be specified.

'capacity' must be of the form 'nnnU' where 'nnn' is a positive integer and
'U' is one of these letters:

    'B' - bytes
    'K' - kilobytes (where 1 kilobyte = 1024 bytes)
    'M' - megabytes (where 1 megabyte = 1024 kilobytes)
    'G' - gigabytes (where 1 gigabyte = 1024 megabytes)
    'T' - terabytes (where 1 terabyte = 1024 gigabytes)

""" + fs_commonUsage
    fs = fs_CachingFilesystem(version="%prog " + fs_fuseVersion,
                              usage = usage, dash_s_do = 'setsingle')
    fs.multithreaded = False

# TODO: add an optional 'nosetatime' option (with no value) to disable our
# "manually" setting the access time on cached files (?) !!!
# - we set it "manually" so that the cache will still work properly when the
#   backing directory is mounted with the 'noatime' mount option
    fs.parser.add_option(mountopt = _fs_cacheDirOption, metavar = "PATH",
        help = "the directory under which to store the cached files")
    fs.parser.add_option(mountopt = _fs_capacityOption, metavar = "SIZE",
        help = "the maximum collective size of all files in the cache " + \
               "(not counting directories)")
    fs.parser.add_option(mountopt = _fs_maxFileCountOption, metavar = "NUM",
        help = "the maximum number of files in the cache (not counting " + \
               "directories)")
    fs.fs_start(usage)
