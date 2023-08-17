# Defines an abstract base class for FUSE filesystems that can be used to
# search a collection of files based on a number of criteria, as well as
# related classes, functions, etc.
#
# NOTE: there is (and should not be) anything in this module that is specific
# to music files: it should be generic enough to apply to any files. In
# particular it shouldn't use the music configuration information.
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
import stat
import time

import sqlite3 as sqlite

from fuse import Direntry
import fuse

from fscommon import debug, report, warn
import fscommon
import utilities as ut


# Constants.

# The name of the main table in a file search database.
_fs_mainTableName = "SEARCH_DATA"

# The name of the column in the main file search database that contains
# the int that uniquely identifies the file.
_fs_idColumnName = "ID"

# The name of the column in the main file search database table that
# contains the file's pathname.
_fs_pathnameColumnName = "PATHNAME"

# The format to use to convert (the uppercase version of) a search key into
# the name of the corresponding column in the main file search database
# table.
#
# Note: the suffix prevents clashes with the names of other "non-key"
# columns in the table.
_fs_keyColumnNameFormat = "%s_KEY"


# The length of the basename of each symlink in the filesystem.
_fs_symlinkLength = 10

# The size of every symlink in a file search directory.
#
# A symlink's size doesn't seem to get used for anything, and using the same
# value for every symlink allows all symlinks in a filesystem to share a
# single stat object.
_fs_symlinkFileSize = 110

# The format to use to convert a file's ID (as a positive int) into the
# basename of a symlink unser a search directory.
_fs_symlinkFormat = "%0." + str(_fs_symlinkLength) + "i"

# the basename of an 'and' directory.
_fs_andDirBasename = "and"


# What to replace pathname separators with in a value in the process of
# converting that value into a valid UNIX pathname component.
#
# See _fs_toPathnameComponent().
_fs_pathnameSeparatorReplacement = "|"

# The pathname component that an empty pathname component is converted into
# in the process of converting the component into a valid pathname component.
_fs_emptyPathnameComponentReplacement = "[[empty]]"


# The maximum size of a (non-permanent) valid directory pathname cache in an
# fs_AbstractFileSearchFilesystem.
_fs_maxValidDirCacheSize = 100


# Functions

def _fs_toPathnameComponent(val):
    """
    Returns the result of converting the value 'val' into a valid UNIX
    pathname component.

    Note: the only characters not allowed in a UNIX pathname component are
    the pathname separator (/) and NUL.
    """
    assert val is not None
    rep = _fs_pathnameSeparatorReplacement
    result = val.replace(os.sep, rep).replace('\0', '')
    if not result:
        result = _fs_emptyPathnameComponentReplacement
    assert result
    return result

def _fs_keyColumnName(key):
    """
    Returns the name of the column in the main file seach database table that
    corresponds to the search key 'key', assuming 'key' is a valid search key
    (that is, we don't check here that it's a valid key).
    """
    assert key is not None
    #assert 'result' is not None
    return _fs_keyColumnNameFormat % key.upper()

def _fs_basenamesToDirentries(names):
    """
    Given a set of valid file basenames returns a list of Direntry objects
    that represent corresponding search directory files.
    """
    #debug("---> in _fs_basenamesToDirentries(names)")
    assert names is not None
    c = list(names)
    #debug("    converted 'names' into a list")
    c.sort()
    #debug("    sorted the list of basenames")
    result = [Direntry(str(k)) for k in c]
        # the 'str()' call converts Unicode strings from sqlite into
        # regular strings (which is what the filesystem code seems to be
        # expecting: otherwise it doesn't list them).
    #debug("    built result: len = %i" % len(result))
    assert result is not None
    assert len(result) == len(names)
    return result

def _fs_fileIdToSymlinkBasename(id):
    """
    Converts the file ID 'id' into the basename of symlink to the
    corresponding file, where the symlink is under a search directory.
    """
    assert id > 0
    result = _fs_symlinkFormat % id
    assert result is not None
    return result

def _fs_symlinkFileId(name):
    """
    Returns the file ID - a positive int - of the file that is linked to by a
    symlink with basename 'name' that is under a search directory, or returns
    None if 'name' isn't a valid basename for such a symlink.

    See _fs_isValidSymlinkBasename().
    """
    assert name is not None
    result = None
    if len(name) == _fs_symlinkLength:
        result = ut.ut_tryToParseInt(name, minValue = 1)
    # 'result' may be None
    return result

def _fs_isSymlinkPathname(path):
    """
    Returns True iff 'path' is the pathname of a symlink in this
    filesystem, assuming it's the pathname of a file in this filesystem.
    """
    result = False
    parts = ut.ut_pathnameComponents(path, os.sep)
    numParts = len(parts)
    if numParts >= 2 and ((numParts - 2) % 3) == 1:
        # 'path' is the pathname of a file in a directory that can
        # contain only symlinks and an 'and' directory, and the 'and'
        # directory's basename isn't a valid symlink basename.
        result = _fs_isValidSymlinkBasename(parts[-1])
    return result


def _fs_isValidSymlinkBasename(name):
    """
    Returns True iff the file basename 'name' is a valid basename for a
    symlink under a search directory.

    See _fs_symlinkFileId().
    """
    assert name is not None
    return (_fs_symlinkFileId(name) is not None)


# Classes.

class fs_FileSearchDatabaseBuilder(object):
    """
    Builds the database file used by an fs_AbstractFileSearchFilesystem.
    """

    def __init__(self, dbPathname, searchKeys):
        """
        Initializes us with the pathname of the database file we're to build
        and a list of the search keys that name each of the criteria that a
        file can be searched for on.

        Note: this method will delete the database file if it already exists,
        prior to replacing it.

        Each item in 'searchKeys' is expected to be a string.
        """
        assert dbPathname is not None

        assert searchKeys  # cannot be None or empty
        self._fs_dbPathname = dbPathname
        ut.ut_deleteFileOrDirectory(dbPathname)
        self._fs_validSearchKeysSet = set(searchKeys)
        conn = sqlite.connect(dbPathname, isolation_level = None)
            # setting isolation_level to 'None' here fixes Python bug #4995
            # that occurs with version 2.5.2 of Python when using
            # transactions: it's supposed to be fixed in version 2.6.?.
        c = conn.cursor()
        self._fs_connection = conn
        self._fs_cursor = c
        #c.execute("pragma synchronous=off")
            # this doesn't speed things up noticeably, and it's unsafe
        self._fs_createTables()
        c.execute("begin transaction")

    def add(self, pathname, searchKeyValueMap):
        """
        Adds to the database the search keys - and corresponding values - that
        are associated with the file with pathname 'pathname'.

        Both the keys and the values in 'searchKeyValueMap' are expected to
        be strings.
        """
        assert pathname is not None
        assert searchKeyValueMap  # cannot be None or empty
        keys = list(searchKeyValueMap)  # creates a new list
        keyCols = ", ".join([_fs_keyColumnName(k) for k in keys])
        holders = ", ".join(["?" for k in keys])
        vals = [_fs_toPathnameComponent(searchKeyValueMap[k]) for k in keys]
            # we convert the values to valid pathname components since the
            # filesystem will compare them to pathname components
        stmt = "insert into %s(%s, %s, %s) values (NULL, ?, %s)" % \
            (_fs_mainTableName, _fs_idColumnName, _fs_pathnameColumnName,
             keyCols, holders)
            # inserting 'NULL' into the _fs_idColumnName column will cause
            # it to be set to the next largest int value: see
            # http://www.sqlite.org/faq.html (question 1) for details.
        args = [pathname] + vals
        #debug("stmt = [%s]" % stmt)
        #debug("args = [%s]" % ", ".join(args))
        #debug("num rows = %s" % self._fs_connection.execute("select count(*) from search_data").fetchall())
        self._fs_cursor.execute(stmt, args)

    def finish(self):
        """
        Called to indicate that we're finished calling 'add()' and that the
        database file can now be built/created.

        Note: this method should always get called.
        """
        conn = self._fs_connection
        cur = self._fs_cursor
        self._fs_connection = None
        self._fs_cursor = None
        #debug("---> in finish(): connection = [%s], cursor = [%s]" % (repr(conn), repr(cur)))
        try:
            #debug("    commiting transaction")
            cur.execute("END TRANSACTION")
            #conn.commit()
        finally:
            try:
                #debug("    close()ing cursor")
                cur.close()
            finally:
                #debug("    close()ing connection")
                conn.close()

    def _fs_createTables(self):
        """
        Creates all of the (initially empty) database tables, as well as
        any and all indexes on those tables.
        """
        table = _fs_mainTableName
        keys = self._fs_validSearchKeysSet
        keyCols = ["%s text" % _fs_keyColumnName(k) for k in keys]
        stmt = "create table %s (%s integer primary key, %s text not null," \
            " %s)" % (table, _fs_idColumnName, _fs_pathnameColumnName,
                      ", ".join(keyCols))
            # NOTE: declaring the _fs_idColumnName column 'INTEGER PRIMARY
            # KEY' will cause it to autoincrement when NULL is inserted into
            # it (as we do in add()): for details see
            # http://www.sqlite.org/faq.html (question 1).
        #debug("---> _fs_createTables(): stmt = [%s]" % stmt)
        c = self._fs_cursor
        c.execute(stmt)

        # Note: making the ID column a primary key (above) already ensures
        # that there's a (unique) index on that column.
        fmt = "create index %s_index on %s (%s)"
        col = _fs_pathnameColumnName
        c.execute(fmt % (col, table, col))
        for k in keys:
            col = _fs_keyColumnName(k)
            c.execute(fmt % (col, table, col))

class _fs_DirectorySearchFileStat(fscommon.fs_AbstractReadOnlyExistingFileStat):
    """
    Represents the result of a stat() call on a directory in a file search
    filesystem.
    """

    def __init__(self, fs, st):
        """
        Initializes us with the filesystem 'fs' that contains the file that
        we're the stat object for, as well as the stat object 'st' for 'fs''s
        original mount subdirectory (i.e. before 'fs' was mounted on it).
        """
        #debug("---> _fs_DirectorySearchFileStat(fs, %s)" % str(st))
        assert fs is not None
        assert st is not None
        fscommon.fs_AbstractReadOnlyExistingFileStat.__init__(self)
        self._fs_createTime = fs.fs_creationTime()
        self._fs_mountDirStat = st
        #debug("    mount dir stat = [%s]" % ut.ut_printableStat(self._fs_mountDirStat))

    def _fs_statsForExistingFile(self):
        # 'result' may be None
        return self._fs_mountDirStat

    def _fs_lastModifiedTime(self):
        #debug("-1-> in _fs_DirectorySearchFileStat._fs_lastModifiedTime()")
        return self._fs_createTime

    def _fs_creationTime(self):
        #debug("-1-> in _fs_DirectorySearchFileStat._fs_creationTime()")
        return self._fs_createTime

class _fs_SymlinkSearchFileStat(_fs_DirectorySearchFileStat):
    """
    Represents the result of a stat() call on a symlink in a file search
    filesystem.
    """

    def _fs_size(self):
        #debug("-0-> in _fs_SymlinkSearchFileStat._fs_size()")
        return _fs_symlinkFileSize

    def _fs_mode(self):
        #debug("-0-> in _fs_SymlinkSearchFileStat._fs_mode()")
        result = _fs_DirectorySearchFileStat._fs_mode(self)
        result = (result & ~stat.S_IFDIR) | stat.S_IFLNK
            # replace part of mode that indicates a dir with a value that
            # indicates a symlink
        #debug("    result = '%o'" % result)
        return result

    def _fs_numberOfLinks(self):
        #debug("-0-> in _fs_SymlinkSearchFileStat._fs_numberOfLinks()")
        return 1


class fs_AbstractFileSearchFilesystem(fscommon.fs_MinimalAbstractReadOnlyFilesystem):
    """
    An abstract base class for read-only FUSE filesystems that can be used to
    search a collection of files based on a number of criteria.
    """

    def __init__(self, *args, **kw):
        """
        Initializes this filesystem.

        Note: our _fs_setValidSearchKeys() and _fs_setDatabasePathname()
        methods must be called after this method is in order to fully
        initialize this instance. (They're usually called from a subclass'
        fs_processOptions() method.)
        """
        #debug("---> fs_AbstractFileSearchFilesystem.__init__()")
        fscommon.fs_MinimalAbstractReadOnlyFilesystem. \
            __init__(self, *args, **kw)
        self._fs_dbPathname = None
        self._fs_validSearchKeysSet = None
        self._fs_connection = None
        self._fs_origMountDirStat = None        # see fs_processOptions()
            # before this filesystem got mounted on it
        self._fs_dirStat = None
        self._fs_symlinkStat = None
        self._fs_creationTime = int(time.time())

        self._fs_permanentValidDirCache = None  # see fs_processOptions()
        self._fs_validDirCache = set()

        # This cache allows us to implement readlink() so that only one SQL
        # SELECT has to be executed to get all of the information for all of
        # the symlinks in a directory (instead of executing a separate SQL
        # SELECT for each symlink).
        self._fs_symlinkCacheDir = None
        self._fs_symlinkCache = None
            # maps the basenames of symlinks in the directory with pathname
            # _fs_symlinkCacheDir to the pathnames of the files they link to

        # This cache allows us to implement getattr() (and possibly others)
        # so that only one SQL SELECT has to be executed to get the basenames
        # of all of the files in a directory (instead of executing a separate
        # SQL SELECT for each file in the directory).
        self._fs_direntryNamesCacheDir = None
        self._fs_direntryNamesCache = None

        # This is supposed to fix problems with corrupted reads of files
        # through these filesystems.
        #
        # We still seem to need it here, even though there are no actual
        # regular files in this filesystem: we get 'Invalid argument' errors
        # when trying to list directories, for example.
        self.multithreaded = False

    def fs_processOptions(self, opts):
        #debug("---> in fs_AbstractFileSearchFilesystem.fs_processOptions(%s)" % str(opts))
        fscommon.fs_MinimalAbstractReadOnlyFilesystem.fs_processOptions(self, opts)
        st = os.stat(self.fs_mountDirectory())
        self._fs_origMountDirStat = st
            # this filesystem hasn't been mounted yet at this point, so these
            # are the stats for the original mount dir
        self._fs_dirStat = _fs_DirectorySearchFileStat(self, st)
        self._fs_symlinkStat = _fs_SymlinkSearchFileStat(self, st)

    def _fs_setDatabasePathname(self, dbPathname):
        """
        Sets to 'dbPathname' the pathname of the database file that contains
        the file search information.
        """
        assert dbPathname is not None
        self._fs_dbPathname = dbPathname
        self._fs_connection = sqlite.connect(dbPathname)

    def _fs_setValidSearchKeys(self, validKeys):
        """
        Sets our list of all of the valid search keys to the ones in the
        list 'validKeys'.

        Note: search keys are assumed to be strings. They will appear in all
        lowercase in the filesystem.
        """
        assert validKeys  # not None or empty
        ks = set([k.lower() for k in validKeys])
        self._fs_validSearchKeysSet = ks
        self._fs_permanentValidDirCache = \
            self._fs_buildPermanentValidDirCache(ks)

    def _fs_buildPermanentValidDirCache(self, searchKeys):
        """
        Builds and returns the set that permanently caches the (canonical
        and non-canonical) pathnames of the most common valid directories,
        using the collection 'searchKeys' of all of the valid search keys.
        """
        #debug("---> _fs_buildPermanentValidDirCache([%s])" % repr(searchKeys))
        assert searchKeys is not None
        result = set()
        sep = os.sep
        result.add(sep)
        for k in searchKeys:
            # We add both canonical and non-canonical versions of each
            # directory to the cache so that pathnames don't have to be
            # canonicalized before being searched for in this cache.
            p = os.path.join(sep, k)
            result.add(p)
            result.add(p + sep)
        #debug("    result = [%s]" % repr(result))
        assert result
        return result

    def _fs_addToValidDirCache(self, path):
        """
        Adds the directory pathname 'path' to the _fs_validDirCache.
        'path' is assumed to be in canonical form.
        """
        assert path
        cache = self._fs_validDirCache
        sz = len(cache)
        mx = _fs_maxValidDirCacheSize
        if sz >= mx:
            # Remove an item from 'cache' to make room for 'path'.
            assert sz == mx
            cache.pop()  # removes arbitrary item
        cache.add(path)
        assert len(cache) <= mx

    def fs_creationTime(self):
        """
        Returns the date/time at which this filesystem was created/mounted,
        in seconds since the Epoch.
        """
        result = self._fs_creationTime
        assert result is not None
        return result


    def _fs_fsdestroy(self):
        conn = self._fs_connection
        if conn is not None:
            conn.close()

    def _fs_readdir(self, path, offset):
        """See readdir()."""
        #debug("---> in fs_AbstractFileSearchFilesystem._fs_readdir(%s)" % path)
        names = self._fs_direntryNames(path)
        if names is not None:
            #debug("    building list of %i Direntries" % len(names))
            result = _fs_basenamesToDirentries(names)
        else:
            result = []
        #debug("    returning list of %i Direntries" % len(result))
        assert result is not None
        return result

    def _fs_getattr(self, path):
        #debug("---> in fs_AbstractFileSearchFilesystem._fs_getattr(%s)" % path)
        # Note: it looks like we have to check here that a file with pathname
        # 'path' actually exists in this filesystem. However it also looks
        # like we can assume that the parent directory of 'path' exists since
        # this method will have been called on its path first.
        if path in self._fs_permanentValidDirCache:
            #debug("    found dir '%s' in permanent dir cache" % path)
            result = self._fs_dirStat
        else:
            cp = ut.ut_toCanonicalDirectory(path)
            if cp in self._fs_validDirCache:
                #debug("    found dir '%s' in dir cache" % path)
                result = self._fs_dirStat
            else:
                isValid = False
                (d, b) = os.path.split(path)
                assert b  # since '/' should be in the permanent cache
                names = self._fs_direntryNames(d)
                if names is not None:  # dir 'd' exists and is valid
                    isValid = (b in names)
                if isValid:
                    if _fs_isSymlinkPathname(path):
                        result = self._fs_symlinkStat
                    else:
                        # All non-symlinks in this filesystem are dirs
                        # (and they can share the same stat object).
                        result = self._fs_dirStat
                        self._fs_addToValidDirCache(cp)
                else:
                    result = fscommon.fs_handleNoSuchFile()
        #debug("    result = [%s]" % ut.ut_printableStat(result))
        assert result is not None
        return result

    def _fs_readlink(self, path):
        #debug("---> in fs_AbstractFileSearchFilesystem._fs_readlink(%s)" % path)
        # Note: we're assuming here that we can only be called on valid
        # symlinks, so we don't have to check that 'path' is the pathname of
        # an existing symlink in this filesystem.
        (d, b) = os.path.split(path)
        if d != self._fs_symlinkCacheDir:
            # Make 'd' the directory whose symlinks we cache.
            self._fs_symlinkCache = self._fs_buildNewSymlinkCache(d)
            self._fs_symlinkCacheDir = d
        result = self._fs_symlinkCache.get(b)
        if result is None:  # can this even happen?
            result = fscommon.fs_handleNoSuchFile()
        #debug("    result = [%s]" % result)
        assert result is not None
        return result

    def _fs_access(self, path, mode):
        #debug("---> in fs_AbstractFileSearchFilesystem._fs_access(%s, %s)" % (path, str(mode)))
        return fscommon.fs_allowEveryoneNonwritingAccess(path, mode)

    def _fs_open(self, path, flags, *mode):
        #debug("---> in fs_AbstractFileSearchFilesystem._fs_open(%s, %s, %s)" % (path, str(flags), mode))
        return fscommon.fs_handleFunctionNotImplemented()
            # since there are only directories and symlinks in this
            # filesystem, neither of which can be open()ed.

    def _fs_read(self, path, length, offset, fd):
        #debug("---> in fs_AbstractFileSearchFilesystem._fs_read(%s, %i, %i, %s)" % (path, length, offset, repr(fd)))
        return fscommon.fs_handleFunctionNotImplemented()
            # since there are only directories and symlinks in this
            # filesystem, neither of which can be read().

    def _fs_flush(self, path, fd):
        #debug("---> in fs_AbstractFileSearchFilesystem._fs_flush(%s, %s)" % (path, repr(fd)))
        pass  # nothing to do since we're a read-only filesystem

    def _fs_release(self, path, flags, fd):
        #debug("---> in fs_AbstractFileSearchFilesystem._fs_release(%s, %i, %s)" % (path, flags, repr(fd)))
        # I'm not sure that this ever gets called: in any case it appears to be
        # impossible to delete files from this filesystem.
        fd.release(flags)

    def _fs_statfs(self):
        #debug("---> in fs_AbstractFileSearchFilesystem._fs_statfs()")
# TODO: is there a good (or at least half-decent) way to implement this ???!!!???
        return fscommon.fs_handleFunctionNotImplemented()


    def _fs_buildNewSymlinkCache(self, d):
        """
        Builds and returns a new symlink cache for the symlinks in the
        directory with pathname 'd'.
        """
        #debug("---> _fs_buildNewSymlinkCache(%s)" % d)
        assert d
        dirParts = ut.ut_pathnameComponents(d)
        (keys, vals, ands) = self._fs_keysValuesAndAndParts(dirParts)
        numVals = len(vals)
        assert len(keys) == numVals  # iff 'd' contains symlinks
        stmt = "select %s, %s from %s" % (_fs_idColumnName,
                                _fs_pathnameColumnName, _fs_mainTableName)
        prefix = "where"
        i = 0
        while i < numVals:
            stmt += (" %s %s = ?" % (prefix, _fs_keyColumnName(keys[i])))
            prefix = "and"
            i += 1
        result = dict([(_fs_fileIdToSymlinkBasename(row[0]),
                        self._fs_adjustSymlinkDestination(str(row[1])))
                    for row in self._fs_executeSql(stmt, vals).fetchall()])
            # the 'str()' call converts from Unicode to 'regular'
            # strings: see the note in _fs_basenamesToDirentries()
        #debug("    result = [%s]" % result)
        assert result is not None
        return result

    def _fs_adjustSymlinkDestination(self, path):
        """
        Returns the result of adjusting the pathname 'path' that is the
        destination of a symlink as specified in the search database. The
        result will be what is ultimately used as the symlink's destination.
        """
        assert path is not None
        result = path
        assert result is not None
        return result


    def _fs_direntryNames(self, path):
        """
        Returns a set of the basenames of all of the files (including
        subdirectories) in the directory in this filesystem with pathname
        'path', or None if there's no directory in this filesystem with that
        pathname.
        """
        #debug("---> in _fs_direntryNames(%s)" % path)
        p = ut.ut_toCanonicalDirectory(path)
        if p == self._fs_direntryNamesCacheDir:
            #debug("    using cached direntry names")
            result = self._fs_direntryNamesCache
        else:
            #debug("    names not in cache")
            result = self._fs_uncachedDirentryNames(p)
            if result is not None:
                #debug("    found names: setting them as the new cache")
                self._fs_direntryNamesCacheDir = p
                self._fs_direntryNamesCache = result
        # 'result' may be None
        return result

    def _fs_uncachedDirentryNames(self, path):
        """
        Returns a set of the basenames of all of the files (including
        subdirectories) in the directory in this filesystem with pathname
        'path', or None if there's no directory in this filesystem with that
        pathname. The set of basenames will NOT be the ones that are cached.

        See _fs_direntryNames().
        """
        result = None
        parts = ut.ut_pathnameComponents(path, os.sep)
        numParts = len(parts)
        if numParts == 1 and not parts[0]:  # path == '/'
            result = self._fs_validSearchKeysSet.copy()
            assert result is not None
        else:
            (keys, vals, ands) = self._fs_keysValuesAndAndParts(parts)
            andDir = _fs_andDirBasename
            mod = numParts % 3
            if [a for a in ands if a != andDir]:
                # One or more of what should be 'and' dirs aren't.
                result = None
            elif len(keys) > len(set(keys)):
                # The same key was used more than once.
                result = None
            elif mod == 1:                          # (k v a)* k
                result = self._fs_keyDirentryNames(keys, vals)
            elif mod == 2:                          # (k v a)* k v
                result = self._fs_valueDirentryNames(keys, vals)
            else:
                # If it's valid it's either a symlink or an 'and' dir.
                assert mod == 0
                last = parts[-1]
                if last == andDir:                  # (k v a)* k v a
                    result = self._fs_validSearchKeysSet.difference(keys)
                    if not result:
                        # We omit 'and' dirs with no keys under them.
                        result = None
                else:                               # (k v a)* k v s
                    result = None  # since you can't readdir() a symlink
        # 'result' may be None
        return result

    def _fs_keysValuesAndAndParts(self, parts):
        """
        Given the list of pathname components 'parts' of a pathname,
        returns a 3-item tuple containing lists of the items in 'parts'
        that contain search keys, values corresponding to search keys,
        and 'and' directories, respectively. However, the third returned list
        will NOT include the last 'and' directory if the pathname is that
        of an 'and' directory.

        The items in each of the returned lists are in the same order as
        they appear in 'parts': thus in particular the i'th item in the
        returned list of values is associated with the i'th item in the
        returned list of search keys.
        """
        assert parts is not None
        numParts = len(parts)
        md = 3
        keys = [parts[i] for i in xrange(0, numParts, md)]
        vals = [parts[i] for i in xrange(1, numParts, md)]
        ands = [parts[i] for i in xrange(2, numParts - 1, md)]
            # won't include last 'and' if pathname is that of an 'and' dir
        result = (keys, vals, ands)
        assert len(result) == 3
        return result

    def _fs_keyDirentryNames(self, keys, vals):
        """
        Returns a set of the basenames of all of the files (including
        subdirectories) in the directory in this filesystem corresponding
        to the keys in the list 'keys' and the associated values in the list
        'vals', or None if there's no such directory in this filesystem.

        The last component of the directory is a search key. The i'th item in
        'vals' is associated with the key that is the i'th item in 'keys'.
        """
        #debug("---> _fs_keyDirentryNames([%s], [%s])" % (repr(keys), repr(vals)))
        assert keys                 # not None or empty
        assert vals is not None     # may be empty, though
        #assert "all keys in 'keys' are distinct"
        numVals = len(vals)
        assert len(keys) == numVals + 1
        colName = _fs_keyColumnName(keys[-1])
        stmt = "select distinct %s from %s" % (colName, _fs_mainTableName)
        prefix = "where"
        i = 0
        while i < numVals:
            stmt += " %s %s = ?" % (prefix, _fs_keyColumnName(keys[i]))
            prefix = "and"
            i += 1
        result = set([row[0] for row in self._fs_executeSql(stmt, vals).
                        fetchall() if row[0] is not None])
        # 'result' may be None
        #debug("    result = [%s]" % repr(result))
        return result

    def _fs_valueDirentryNames(self, keys, vals):
        """
        Returns a set of the basenames of all of the files (including
        subdirectories) in the directory in this filesystem corresponding
        to the keys in the list 'keys' and the associated values in the list
        'vals', or None if there's no such directory in this filesystem.

        The last component of the directory is a value associated with the
        lat key in 'keys'. The i'th item in 'vals' is associated with the key
        that is the i'th item in 'keys'.
        """
        #debug("---> _fs_valueDirentryNames([%s], [%s])" % (repr(keys), repr(vals)))
        assert keys                 # not None or empty
        assert vals is not None     # may be empty, though
        #assert "all keys in 'keys' are distinct"
        numKeys = len(keys)
        assert numKeys == len(vals)
        result = None
        stmt = "select %s from %s" % (_fs_idColumnName, _fs_mainTableName)
        prefix = "where"
        i = 0
        while i < numKeys:
            stmt += " %s %s = ?" % (prefix, _fs_keyColumnName(keys[i]))
            prefix = "and"
            i += 1
        result = set([_fs_fileIdToSymlinkBasename(row[0]) for row in \
            self._fs_executeSql(stmt, vals).fetchall()])
        if result and numKeys < len(self._fs_validSearchKeysSet):
            # Add an 'and' subdir iff there're keys left to go under it and
            # at least the possibility that they'll be non-empty.
            result.add(_fs_andDirBasename)
        # 'result' may be None
        return result

    def _fs_executeSql(self, stmt, vals):
        """
        Executes the SQL statement 'stmt' with the values 'vals' and returns
        a cursor that can be used to access the results.
        """
        #debug("---> _fs_executeSql(%s, [%s])" % (stmt, ", ".join(vals)))
        assert stmt
        assert vals is not None
        result = self._fs_connection.execute(stmt, vals)
        assert result is not None
        return result
