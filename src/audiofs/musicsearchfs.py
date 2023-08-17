# Defines a class that implements a FUSE filesystem that allows a music
# directory to be searched based on a number of criteria.
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

from filesearchfs import fs_AbstractFileSearchFilesystem
import filesearchfs
import musicfs

from fscommon import debug, report, warn
import fscommon
import utilities as ut


# Constants.

# Option names.
fs_dbOption = "db"
fs_catalogueOption = "catalogue"
fs_baseDirOption = "base"
fs_searchTagsOption = "tags"

# The separator between tag names in the value of this filesystem's
# 'tags' suboption
fs_tagSeparator = ":"

# The keys to associate with the format and kind of a music file in the search
# directory.
_fs_formatSearchKey = "FORMAT"
_fs_kindSearchKey = "KIND"
_fs_originalSearchKey = "ORIGINAL"

# The values associated with search keys that can have yes or no values.
_fs_yesValue = "yes"
_fs_noValue = "no"


# Functions.

def fs_rebuildSearchDatabaseFile(dbPathname, catalogue, searchKeys):
    """
    (Re)builds the search database file with pathname 'dbPathname' using the
    information from the music catalogue file with pathname 'catalogue'. The
    search database will contain the search keys in the list 'searchKeys'.

    See fs_tagsToKeys().
    """
    assert dbPathname
    assert catalogue
    assert searchKeys  # not None or empty
    b = _fs_MusicSearchDatabaseBuilder(dbPathname, searchKeys)
    b.fs_parse(catalogue)

def fs_tagsToKeys(tags):
    """
    Returns the list of search keys corresponding to the list of music file
    tag names 'tags'.
    """
    assert tags is not None
    result = [_fs_formatSearchKey, _fs_kindSearchKey, _fs_originalSearchKey]
    result.extend(tags)
    #assert result is not None
    assert len(result) >= len(tags)
    return result


# Classes.

class _fs_MusicSearchDatabaseBuilder(musicfs.fs_AbstractMusicDirectoryCatalogueParser):
    """
    Builds from a music directory's catalogue the database used by a file
    search filesystem to search that music directory.
    """

    def __init__(self, dbPathname, searchKeys):
        """
        Initializes us with the pathname 'dbPathname' of the file search
        filesystem database file we're to build and a list 'searchKeys' of
        all of the valid search keys.
        """
        assert dbPathname is not None
        assert searchKeys  # not None or empty
        musicfs.fs_AbstractMusicDirectoryCatalogueParser.__init__(self)
        import filesearchfs
            # we import this here so that its dependencies are required only
            # if there's a (nonempty) search directory
        self._fs_dbBuilder = filesearchfs. \
            fs_FileSearchDatabaseBuilder(dbPathname, searchKeys)
        self._fs_searchKeys = searchKeys

    def _fs_processFileInformation(self, info):
        #debug("---> in _fs_MusicSearchDatabaseBuilder._fs_processFileInformation(info)")
        assert info is not None  # and is a fs_CataloguedFileInformation object.
        b = self._fs_dbBuilder
        kv = {}
        for k in self._fs_searchKeys:
            v = info.fs_tagValue(k)
            if v is None:
                # Tags with the same name as 'predefined' search keys
                # override the predefined search keys.
                if k == _fs_formatSearchKey:
                    v = musicfs.fs_fileFormatFromInformation(info)
                elif k == _fs_kindSearchKey:
                    v = musicfs.fs_fileKindFromInformation(info)
                elif k == _fs_originalSearchKey:
                    if info.fs_isOriginalFile():
                        v = _fs_yesValue
                    else:
                        v = _fs_noValue
                # Otherwise the music file doesn't have tag 'k'.
            if v is not None:
                kv[k] = v
        b.add(info.fs_pathname(), kv)

    def _fs_afterParsing(self):
        #debug("---> in _fs_MusicSearchDatabaseBuilder._fs_afterParsing()")
        musicfs.fs_AbstractMusicDirectoryCatalogueParser._fs_afterParsing(self)
        self._fs_dbBuilder.finish()


class fs_MusicSearchFilesystem(fs_AbstractFileSearchFilesystem):
    """
    Represents read-only filesystems that can be used to search a music
    directory based on a number of criteria.
    """

    def __init__(self, *args, **kw):
        """
        Initializes this filesystem.
        """
        fs_AbstractFileSearchFilesystem.__init__(self, *args, **kw)
        self._fs_baseDir = ""

    def fs_processOptions(self, opts):
        fs_AbstractFileSearchFilesystem.fs_processOptions(self, opts)

        tags = fscommon.fs_parseRequiredSuboption(opts, fs_searchTagsOption)
        #debug("---> process opts: tags = [%s]" % tags)
        tags = [t.strip() for t in tags.split(fs_tagSeparator)]
        keys = fs_tagsToKeys(tags)
        self._fs_setValidSearchKeys(keys)

        baseDir = fscommon.fs_parseOptionalSuboption(opts, fs_baseDirOption)
        if baseDir is not None:
            self._fs_baseDir = baseDir

        db = ut.ut_expandedAbsolutePathname(fscommon.
                        fs_parseRequiredSuboption(opts, fs_dbOption))
        self._fs_setDatabasePathname(db)

        cat = fscommon.fs_parseOptionalSuboption(opts, fs_catalogueOption)
        if cat is not None:
            cat = ut.ut_expandedAbsolutePathname(cat)
            fs_rebuildSearchDatabaseFile(db, cat, keys)

    def _fs_adjustSymlinkDestination(self, path):
        assert path is not None
        result = os.path.join(self._fs_baseDir, path)
        assert result is not None
        return result


# Main method.

def main():
    """
    Main method.
    """
    # musicsearchfs -o db=PATH tags=TAGS [catalogue=PATH] [base=PATH] mountpoint
    usage = """

A filesystem that allows a music directory's contents to be searched
based on a number of criteria.

""" + fscommon.fs_commonUsage
    fs = fs_MusicSearchFilesystem(version="%prog " + fscommon.fs_fuseVersion,
                                  usage = usage, dash_s_do = 'setsingle')
    fs.parser.add_option(mountopt = fs_dbOption, metavar = "PATH",
        help = "the pathname of the search database file: it must already exist unless the '%s' mount option is also specified" % fs_catalogueOption)
    fs.parser.add_option(mountopt = fs_searchTagsOption, metavar = "TAGS",
        help = "a colon-separated list of the music file tags that can " \
               "be searched on")
    fs.parser.add_option(mountopt = fs_catalogueOption, metavar = "PATH",
        help = "if present, the pathname of the music catalogue file to use to (re)build the search database file")
    fs.parser.add_option(mountopt = fs_baseDirOption, metavar = "PATH",
        help = "if present, the pathnames of all of the music files (as obtained from a music catalogue) will be assumed to be relative to PATH")
    fs.fs_start(usage)
