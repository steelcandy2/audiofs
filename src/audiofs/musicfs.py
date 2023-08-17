# Defines an abstract base class for our music FUSE filesystems, as well as
# related constants, functions, etc.
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

import xml.sax
import anydbm
import shelve
import random
import time

from fuse import Direntry

import music
import mergedfs
from fscommon import debug, report, warn
import fscommon
import config
import utilities as ut


# Constants.

_conf = config.obtain()

# Option names.
fs_bitrateOption = "bitrate"
fs_flacDirOption = "flac"


# The name of the tag in an "origins" metadata file whose value is the
# pathname of the file that the file being described represents a part of.
fs_containerOriginsTagName = "CONTAINER"

# The name of the tag in an "origins" metadata file whose value is the
# pathname of the file that is an index into the files contained in the
# file whose pathname is the value of the tag whose name is given by the
# value of 'fs_containerOriginsTagName'.
#
# A file should contain a tag with this name only if it also contains one
# whose name is given by the value of 'fs_containerOriginsTagName'.
fs_containerIndexOriginsTagName = "CONTAINER_INDEX"

# The name of the tag in an "origins" metadata file whose value is the
# pathname of the non-"real" file that the file being described is a copy
# of, possibly encoded in a different format and/or at a different level
# of quality.
fs_originalOriginsTagName = "ORIGINAL"

# The name of the tag in an "origins" metadata file whose value is the
# pathname of the "real" file that the file being described is a mirror
# of.
fs_realOriginalOriginsTagName = "REAL_ORIGINAL"

# The name of the tag in a "derived" metadata file whose value is the
# duration, in seconds, of the audio in a file.
fs_durationInSecondsDerivedTagName = "DURATION_IN_SECONDS"


# The extension to use in the basenames of metadata files that contain
# information about the origins of the file being described.
_fs_originsMetadataFileExtension = "origins"

# The metadata file extension for metadata files that contain a music
# file's tags.
fs_tagsMetadataFileExtension = "tags"

# The extension to use in the basenames of metadata files that contain
# metadata derived from the file itself.
_fs_derivedMetadataFileExtension = "derived"

# The basenames and pathnames of all of the files in the summaries metadata
# directory for an fs_AbstractMusicFilesystem.
_fs_catalogueSummaryMetadataFileBasename = "catalogue.xml"
_fs_catalogueSummaryMetadataFilePathname = \
    os.path.join(mergedfs.fs_summariesMetadataSubdirPathname,
                 _fs_catalogueSummaryMetadataFileBasename)
_fs_relativeCatalogueSummaryMetadataFilePathname = \
    os.path.join(mergedfs.fs_relativeSummariesMetadataSubdirPathname,
                 _fs_catalogueSummaryMetadataFileBasename)

_fs_summaryMetadataFileBasenames = [_fs_catalogueSummaryMetadataFileBasename]
_fs_summaryMetadataFileDirentries = [Direntry(name) for name in \
    _fs_summaryMetadataFileBasenames]
_fmt = os.path.join(mergedfs.fs_summariesMetadataSubdirPathname, "%s")
_fs_summaryMetadataFilePathnames = \
    [_fmt % name for name in _fs_summaryMetadataFileBasenames]


# The string that terminates the track number part of a single-track
# music file's base filename in a music filesystem.
_fs_trackNumberTerminator = "_"

# A list of the extensions for each and every metadata file for each
# non-metadata music file in a music filesystem, at least by default.
_fs_defaultAllMetadataFileExtensions = [
    mergedfs.fs_pathnameMetadataFileExtension,
    fs_tagsMetadataFileExtension, _fs_originsMetadataFileExtension,
    _fs_derivedMetadataFileExtension]

# The maximum number of characters allowed in the simplified version of a
# filename (see _fs_simplifyFilename()).
_fs_maxCharsInSimplifiedFilename = 100


# The minimum number of entries that have to be in a directory in an
# fs_AbstractMusicFilesystem in order for information about the directory's
# files/entries to get cached by the filesystem.
#
# TODO: make this "externally" configurable???!!!???
_fs_minCacheableDirSize = 30

# The minimum size (in bytes) that a temporary cached file in an
# fs_AbstractMusicFilesystem must have before we start to read any data from
# it.
_fs_minTempGeneratedFileSize = (64 * 1024) - 1
#_fs_minTempGeneratedFileSize = 0


# The basenames of the DBM files used to hold various types of information
# about music files.
_fs_originalPathnameToRatingDbmFilenameFmt = \
    "original-pathname-to-%s-rating.db"
_fs_pathnameToOriginalPathnameDbmFilename = "pathname-to-original.db"
_fs_pathnameToInfoShelfFilename = "pathname-to-info.db"

# The basename of the music search directory database file.
_fs_searchDatabaseFilename = "search.db"

# The string that, if it is the first thing in a line from a ratings file,
# indicates that the line is a comment and so should be ignored.
_fs_ratingsFileCommentStart = "#"

# The format of a non-empty, non-comment line in a ratings file.
_fs_ratingsFileLineFmt = "%(rating)4i %(path)s"

# The format of error and debugging messages output by change ratings
# daemon processes.
_fs_daemonMessageFormat = "CHANGE RATINGS DAEMON: %s"

# The valid values for the "refresh" ratings command argument that
# specifies the type of refreshing to do.
_fs_externalRefreshType = "external"
_fs_internalRefreshType = "internal"
_fs_allRatingsRefreshTypes = [_fs_internalRefreshType,
                              _fs_externalRefreshType]

# The name of the "refresh" ratings command, and the format of the command.
_fs_refreshRatingsCommand = "refresh"
_fs_refreshRatingsCommandFmt = "%s %s %s" % \
    (_fs_refreshRatingsCommand, "%(base)s", "%(type)s")


# The basenames of the various generated playlists.
_fs_everythingPlaylistFilename = ut.ut_addExtension("everything",
                                    config.fullDefaultPlaylistExtension)
_fs_originalsPlaylistFilename = ut.ut_addExtension("originals",
                                    config.fullDefaultPlaylistExtension)
_fs_allGeneratedPlaylistFilenames = [_fs_everythingPlaylistFilename,
                                     _fs_originalsPlaylistFilename]

# The start of the basename of the temporary files used to hold the
# pathnames of candidates for inclusion in a playlist.
_fs_tempPlaylistCandidatesPrefix = "playlist-candidates-"


# The string used to indent a line one level in a directory catalogue.
#
# See fs_catalogueFilesUnder().
_fs_oneCatalogueIndentLevel = "    "

# The string used to indent the first line of a file XML element in a
# directory catalogue.
_fs_fileElementIndent = _fs_oneCatalogueIndentLevel

# Element names used in directory catalogues.
_fs_catalogueElementName = "catalogue"
_fs_fileElementName = "file"
_fs_startDirElementName = "directory-start"
_fs_endDirElementName = "directory-end"
_fs_metadataElementName = "metadata"
_fs_categoryElementName = "category"
_fs_categoryItemElementName = "item"

# Attribute names used in directory catalogues.
_fs_baseDirAttributeName = "basedir"
_fs_pathnameAttributeName = "pathname"
_fs_lastModifiedTimeAttributeName = "mtime"
_fs_categoryNameAttributeName = "name"
_fs_categoryItemNameAttributeName = "name"
_fs_fileCountAttributeName = "file-count"
_fs_subdirCountAttributeName = "subdir-count"

# Format strings used in building a directory catalogue.
_fs_xmlHeaderFmt = '<?xml version="1.0"?>\n'
_fs_catalogueStartFmt = '<%s %s="%s">\n' % (_fs_catalogueElementName,
    _fs_baseDirAttributeName, "%(baseDir)s")
_fs_catalogueEndFmt = '</%s>\n' % _fs_catalogueElementName
_fs_fileStartFmt = '%s<%s %s="%s" %s="%s">' % ("%(indent)s",
    _fs_fileElementName, _fs_pathnameAttributeName, "%(pathname)s",
    _fs_lastModifiedTimeAttributeName, "%(mtime)i")
_fs_fileEndFmt = '%s</%s>\n' % ("%(indent)s", _fs_fileElementName)

_fs_startDirFmt = '%s<%s %s="%s" %s="%s" %s="%s"/>\n' % ("%(indent)s",
    _fs_startDirElementName, _fs_pathnameAttributeName, "%(pathname)s",
    _fs_fileCountAttributeName, "%(num-files)i",
    _fs_subdirCountAttributeName, "%(num-subdirs)i")
_fs_endDirFmt = '%s<%s %s="%s" %s="%s" %s="%s"/>\n' % ("%(indent)s",
    _fs_endDirElementName, _fs_pathnameAttributeName, "%(pathname)s",
    _fs_fileCountAttributeName, "%(num-files)i",
    _fs_subdirCountAttributeName, "%(num-subdirs)i")
_fs_metadataStartFmt = '%s<%s>' % ("%(indent)s", _fs_metadataElementName)
_fs_metadataEndFmt = '%s</%s>' % ("%(indent)s", _fs_metadataElementName)
_fs_categoryStartFmt = '%s<%s %s="%s">' % ("%(indent)s",
    _fs_categoryElementName, _fs_categoryNameAttributeName, "%(name)s")
_fs_categoryEndFmt = '%s</%s>' % ("%(indent)s", _fs_categoryElementName)
_fs_categoryItemFmt = '%s<%s %s="%s">%s</%s>' % ("%(indent)s",
    _fs_categoryItemElementName, _fs_categoryItemNameAttributeName,
    "%(name)s", "%(value)s", _fs_categoryItemElementName)

# Names of categories of metadata about files in a directory catalogue.
_fs_originsMetadataCategoryName = _fs_originsMetadataFileExtension
_fs_tagsMetadataCategoryName = fs_tagsMetadataFileExtension
_fs_derivedMetadataCategoryName = _fs_derivedMetadataFileExtension

# The prefix for name of the temporary directory used in processing a
# music directory catalogue in order.
_fs_tempCatalogueDirPrefix = "tmp-music-catalogue-"


# The basename of the FIFO to which to write commands to change a music
# file's rating in a given ratings file.
_fs_changeRatingCommandSinkFilename = "change-ratings.sink"


# The separator between fields in each line of a raw documentation data file.
_fs_rawDocDataFieldSeparator = '\0'

# The basenames of the files containing the generated documentation
# describing all of the (original) albums and tracks in our main music
# catalogue.
_fs_albumsDocumentationFilename = "albums.html"
_fs_tracksDocumentationFilename = "tracks.html"

# The value used by default in a field in generated documentation when there's
# no value for that field.
_fs_defaultDocFieldValue = "?"

# A list of track titles: if a track's title is one of the ones in this list
# then it shouldn't appear in generated documentation (except possibly in
# commented out or otherwise hidden forms).
_fs_trackTitlesToHideInDocs = [_fs_defaultDocFieldValue, "", " ",
                               "[data]", "[blank]"]


# The names of some of the ratings to chances conversion methods.
defaultRatingConverterName      = "default"
plusOneRatingConverterName      = "plusOne"
equalRatingConverterName        = "equal"
nonzeroEqualRatingConverterName = "nonzeroEqual"
averageRatingConverterName      = "average"
okRatingConverterName           = "ok"
goodRatingConverterName         = "good"
betterRatingConverterName       = "better"
bestRatingConverterName         = "best"
minValueRatingConverterNamePrefix = "min"

# The minimum ratings for synonyms to min'n' rating-to-chances methods.
averageMinRating    = 5
okMinRating         = 6
goodMinRating       = 7
betterMinRating     = 8
bestMinRating       = 9

# A map from the names of rating-to-chances conversion methods to the
# one-argument functions that perform the corresponding conversion. Its
# value is set before it's used for the first time.
_fs_ratingToChancesConverterNameToFunctionMap = None


# Exception classes.

class fs_MissingCatalogueException(Exception):
    """
    The class of exception raised when a filesystem's catalogue summary
    metadata file is missing and it's required to exist.
    """
    pass


# Functions

def fs_parseBitrateOptionValue(val, default):
    """
    Parses the option value 'val' as a bitrate for a music file, returning
    'default' if 'val' is None, returning the result of parsing 'val' if 'val'
    is a valid (positive) bitrate, or throwing an appropriate
    fs_OptionParsingException otherwise.
    """
    assert default > 0
    if val is None:
        result = default
        assert val > 0
    else:
        try:
            result = int(val)
        except ValueError:
            msg = "'%s' is not a valid bitrate: it must be a positive " \
                  "integer." % val
            raise fscommon.fs_OptionParsingException(msg)
        if result <= 0:
            msg = "The bitrate must be a positive integer."
            raise fscommon.fs_OptionParsingException(msg)
    assert result > 0
    return result


def fs_changeRatingCommandSink():
    """
    Returns the pathname of the FIFO to which to write commands to change a
    music file's rating in a given ratings file.
    """
    result = _fs_changeRatingCommandSinkFilename
    result = os.path.join(_conf.systemDir, result)
    assert result is not None
    return result


def _fs_openMetadataDbmFile(f, flag = 'r'):
    """
    Opens, in the manner specified by the flag 'flag', the metadata DBM file
    with basename 'f' and returns the mapping object corresponding to it.
    """
    assert f is not None
    assert flag is not None
    result = _fs_openDbmFile(_fs_metadataDatabaseFilePathname(f), flag)
    assert result is not None
    return result

def _fs_metadataDatabaseFilePathname(f):
    """
    Returns the pathname of the metadata database (such as DBM or shelf)
    file with basename 'f'.
    """
    assert f is not None
    result = os.path.join(_conf.metadataDir, f)
    assert result is not None
    return result

def fs_searchDatabasePathname():
    """
    Returns the pathname of the database used by music search filesystems.
    """
    f = _fs_searchDatabaseFilename
    result = _fs_metadataDatabaseFilePathname(f)
    assert result is not None
    return result

def _fs_openRatingsDbmFile(base, flag = 'r'):
    """
    Opens, in the manner specified by the flag 'flag', the original file
    pathname to rating DBM file corresponding to the ratings file with base
    name 'base' and returns the mapping object corresponding to it.
    """
    assert base
    assert flag is not None
    path = _fs_originalPathnameToRatingDbmFilePathname(base)
    result = _fs_openDbmFile(path, flag)
    assert result is not None
    return result

def _fs_originalPathnameToRatingDbmFilePathname(base):
    """
    Returns the pathname of the DBM file that maps the pathnames of original
    files to the rating from the ratings file with base name 'base'.
    """
    assert base
    result = _fs_originalPathnameToRatingDbmFilenameFmt % base
    result = os.path.join(_conf.ratingsDir, result)
    assert result is not None
    return result

def _fs_openDbmFile(path, flag = 'r'):
    """
    Opens, in the manner specified by the flag 'flag', the DBM file with
    pathname 'path' and returns the mapping object corresponding to it.
    """
    assert path is not None
    assert flag is not None
    result = anydbm.open(path, flag)
    assert result is not None
    return result

def _fs_openShelfFile(path, flag = 'r'):
    """
    Opens, in the manner specified by the flag 'flag', the shelf file with
    pathname 'path' and returns the mapping object corresponding to it.
    """
    assert path is not None
    assert flag is not None
    result = shelve.open(path, flag)
    assert result is not None
    return result


def fs_ratingsFilePathname(base):
    """
    Returns the pathname of the ratings file with base name 'base'.
    """
    assert base is not None
    result = ut.ut_addExtension(base, config.ratingsFileExtension)
    result = os.path.join(_conf.ratingsDir, result)
    assert result is not None
    return result

def _fs_findNewRating(m, path, default = None, prefix = None):
    """
    If the map/dictionary 'm' isn't None then it's assumed to be an original
    file pathname to ratings map and we look up the rating corresponding to
    the orginal file pathname 'path', returning it - an int value - if it's
    found and returning 'default' otherwise.

    By default 'path' is assumed to have come from a ratings file, where all
    of the pathnames are relative to the base music directory. But the
    pathnames in original file pathname to ratings maps are relative to the
    ROOT music directory, so by default - that is, when 'prefix' is None - we
    prepend the appropriate pathname prefix (namely _conf.baseSubdir) to
    'path' to get the key we look up in 'm'. But if 'prefix' isn't None then
    we prepend 'prefix' instead.
    """
    # 'm' may be None
    assert path is not None
    assert default is None or default >= 0
    # 'prefix' may be None
    if m is None:
        result = default
    else:
        if prefix is None:
            prefix = _conf.baseSubdir
        key = str(os.path.join(prefix, path))
        if key in m:
            result = m[key]
        else:
            result = default
        if result is not None:
            result = int(result)
    assert result == default or result >= 0
    return result

def _fs_buildRatingToChancesConverterNameToFunctionMap():
    """
    Builds and returns a map that maps the names of the rating-to-chances
    conversion methods to the one-argument functions that map ratings to
    chances.
    """
    result = {}
    result[defaultRatingConverterName] = fs_defaultRatingToChancesConverter
    result[plusOneRatingConverterName] = fs_plusOneRatingToChancesConverter
    result[equalRatingConverterName] = fs_equalRatingToChancesConverter
    result[nonzeroEqualRatingConverterName] = \
        fs_equalIfNonzeroRatingToChancesConverter

    prefix = minValueRatingConverterNamePrefix
    minFunc = fs_minimumRatingToChancesConverter
    fmt = "%s%i"
    for minRating in range(config.maxRating + 1):
        f = lambda r, m = minRating, fn = minFunc: fn(r, m)
        result[fmt % (prefix, minRating)] = f

    result[averageRatingConverterName] = \
        result[fmt % (prefix, averageMinRating)]
    result[okRatingConverterName] = result[fmt % (prefix, okMinRating)]
    result[goodRatingConverterName] = result[fmt % (prefix, goodMinRating)]
    result[betterRatingConverterName] = \
        result[fmt % (prefix, betterMinRating)]
    result[bestRatingConverterName] = result[fmt % (prefix, bestMinRating)]

    assert result is not None
    return result

def fs_ratingToChancesConverter(name):
    """
    Returns the one-argument function corresponding to the name 'name' that
    maps a file's rating to its chances of appearing in a playlist, or
    returns None if there is no such function corresponding to 'name'.
    """
    global _fs_ratingToChancesConverterNameToFunctionMap
    m = _fs_ratingToChancesConverterNameToFunctionMap
    if m is None:
        m = _fs_buildRatingToChancesConverterNameToFunctionMap()
        _fs_ratingToChancesConverterNameToFunctionMap = m
    result = m.get(name, None)
    # 'result' may be None
    return result


def fs_fileFormatFromInformation(info):
    """
    Returns the file format obtained from the fs_CataloguedFileInformation
    object 'info', or returns None if it couldn't be obtained.
    """
    #debug("---> in fs_fileFormatFromInformation(info)")
    result = None
    i = _conf.rootFormatPathnameComponentIndex
    #debug("    i = %i" % i)
    p = info.fs_pathname()
    #debug("    pathname = [%s]" % p)
    assert not os.path.isabs(p)
    parts = p.split(os.sep)
    if i < len(parts):
        result = parts[i]
    # 'result' may be None
    #debug("    result = %s" % result)
    return result

def fs_fileKindFromInformation(info):
    """
    Returns the file kind obtained from the fs_CataloguedFileInformation
    object 'info', or returns None if it couldn't be obtained.
    """
    #debug("---> in fs_fileKindFromInformation(info)")
    result = None
    i = _conf.rootKindPathnameComponentIndex
    #debug("    i = %i" % i)
    p = info.fs_pathname()
    #debug("    pathname = [%s]" % p)
    assert not os.path.isabs(p)
    parts = p.split(os.sep)
    if i < len(parts):
        result = parts[i]
    # 'result' may be None
    #debug("    result = %s" % result)
    return result

def fs_fileGenreFromInformation(info):
    """
    Returns the music genre obtained from the fs_CataloguedFileInformation
    object 'info', or returns None if it couldn't be obtained.
    """
    result = info.fs_tagValue(music.mu_flacGenreTag)
    # 'result' may be None
    return result


def fs_mergeCatalogues(mountPoints, w, allMustExist = True):
    """
    Merges the catalogue summary metadata files for each of the audio
    filesystems whose mount points are in 'mountPoints' into a single
    catalogue that is written out using the file object 'w'.

    If 'allMustExist' is True then an fs_MissingCatalogueException is raised
    if one or more of the filesystems doesn't have a catalogue summary
    metadata file; otherwise missing catalogue files are silently ignored and
    the final catalogue will be the result of merging those catalogue files
    that do exist.
    """
    #debug("---> in fs_mergeCatalogues([%s], w, %s)" % (", ".join(mountPoints), str(allMustExist)))
    assert mountPoints is not None
    assert w is not None
    join = os.path.join
    relCatPath = _fs_relativeCatalogueSummaryMetadataFilePathname
    #debug("    relCatPath = [%s]" % relCatPath)
    catPaths = []
    for mp in mountPoints:
        #debug("    adding catalogue for fs with mount point [%s]" % mp)
        cp = join(mp, relCatPath)
        if os.path.isfile(cp):
            #debug("    catalogue exists")
            catPaths.append(cp)
        else:
            msg = "the catalogue summary metadata file '%s'\nfor the " \
                "audio filesystem mounted at '%s'\ndoesn't exist or isn't " \
                "a regular file" % (cp, mp)
            if allMustExist:
                raise fs_MissingCatalogueException(msg)
            else:
                warn(msg)
    if catPaths:
        # Note: we 'hardcode' the rootDir here since it's what the pathnames
        # of all of the files in the catalogue summary metadata files are
        # relative to.
        #debug("   merging %i filesystems' catalogues together" % len(catPaths))
        b = fs_MergingSortedMusicDirectoryCatalogueBuilder(catPaths,
                                                           _conf.rootDir)
        #debug("    created merging catalogue builder")
        b.build(w)
        #debug("    finished building merged catalogue")
    else:
        warn("there are no catalogue summary metadata files to merge")

def fs_explodeMusicDirectoryCatalogue(catalogue, destDir):
    """
    Explodes the music directory catalogue XML file with pathname 'catalogue'
    into files under the directory with pathname 'destDir', where each file
    will contain the XML element describing one audio file.
    """
    assert catalogue is not None
    assert os.path.isabs(catalogue)
    assert destDir is not None
    assert os.path.isabs(destDir)
    assert os.path.isdir(destDir)
    p = fs_MusicDirectoryCatalogueExploder(destDir)
    p.fs_parse(catalogue)

def fs_buildCatalogueFileElementFormatForAlbumTracks(albumPath, cuePath,
                        relAlbumPath, relCuePath, relTracksDir):
    """
    Builds and returns a format string that can be used to build the music
    directory catalogue file XML element for any track on the album whose
    FLAC and CUE files have pathnames 'albumPath' and 'cuePath',
    respectively. The album's FLAC and CUE files will have pathnames
    'relAlbumPath' and 'relCuePath', respectively, in the returned file
    element format string, and the track's pathname in it will start with
    'relTracksDir'.

    When it's used the returned format will expect to be used with a map
    with the following items:
        - 'basename': mapped to the track file's basename
        - 'trackNumber': mapped to the track's 1-based track number, as a
          properly formatted string (that is, the format doesn't add leading
          zeroes or anything)
        - 'title': the track's title
        - 'artist': the name of the artist that performs the track
    We assume that each value in the map has been quoted to be valid XML
    (using ut.ut_quoteForXml(), for example).
    """
    #debug("---> in function musicfs.fs_buildCatalogueFileElementFormatForAlbumTracks(%s, %s, %s, %s, %s)" % (albumPath, cuePath, relAlbumPath, relCuePath, relTracksDir))
    assert albumPath is not None
    assert cuePath is not None
    assert relAlbumPath is not None
    assert relCuePath is not None
    assert relTracksDir is not None
    indent = _fs_fileElementIndent
    in2 = indent + _fs_oneCatalogueIndentLevel
    in3 = in2 + _fs_oneCatalogueIndentLevel
    lines = []
    quote = ut.ut_quoteForStringFormat

    #debug("    building element start ...")
    mtime = _fs_cataloguedFileLastModifiedTime(albumPath)
    #debug("        mtime = %i" % mtime)
    relPath = os.path.join(quote(relTracksDir), "%(basename)s")
    #debug("        relPath = [%s]" % relPath)
    lines.append(_fs_fileCatalogueElementStart(relPath, mtime, indent))
    lines.append(_fs_metadataStartFmt % { "indent": in2 })

    #debug("    building origins subelement ...")
    catName = _fs_originsMetadataCategoryName
    m = {
        fs_containerOriginsTagName: quote(relAlbumPath),
        fs_containerIndexOriginsTagName: quote(relCuePath)
    }
    _fs_appendFileCategoryCatalogueLines(lines, catName, m, in3)

    #debug("    building tags subelement ...")
    catName = _fs_tagsMetadataCategoryName
    tagsMap = music.mu_tagsMap(albumPath)
    m = {}
    for (k, v) in tagsMap.items():
        m[k] = quote(v)
    assert len(m) == len(tagsMap)
    m[music.mu_flacTrackNumberTag] = "%(trackNumber)s"
    m[music.mu_flacTrackTitleTag] = "%(title)s"
    m[music.mu_flacArtistTag] = "%(artist)s"
    _fs_appendFileCategoryCatalogueLines(lines, catName, m, in3)

    #debug("    building derived subelement ...")
    catName = _fs_derivedMetadataCategoryName
    m = _fs_buildDerivedMetadataMap("%(durationInSeconds)s")
    _fs_appendFileCategoryCatalogueLines(lines, catName, m, in3)

    #debug("    building end of element ...")
    lines.append(_fs_metadataEndFmt % { "indent": in2 })
    lines.append(_fs_fileCatalogueElementEnd(indent))
    result = "\n".join(lines)
    #debug("    done building result")
    assert result is not None
    return result

def _fs_buildDerivedMetadataMap(durationInSeconds):
    """
    Builds and returns a map containing the specified metadata information
    for a music file, which is presumed to be dervied from the file itself.
    """
    assert durationInSeconds >= 0 or durationInSeconds == -1
    if durationInSeconds < 0:
        result = { }
    else:
        result = {
            fs_durationInSecondsDerivedTagName: str(durationInSeconds) }
    assert result is not None  # though it may be empty
    return result

def _fs_cataloguedFileLastModifiedTime(path):
    """
    Returns the last modified date/time for the file with pathname 'path'
    in the format used in music directory catalogues.
    """
    #debug("---> in function _fs_cataloguedFileLastModifiedTime(%s)" % path)
    assert path is not None
    result = os.path.getmtime(path)
    #debug("   prelim result = [%s]" % result)
    result = int(result)
    #debug("   final result = %i" % result)
    assert result >= 0
    return result

def _fs_catalogueCompareFilePathnames(path1, path2):
    """
    Compares the pathnames 'path1' and 'path2' of two non-directory files,
    returning 0 iff 'path1' and 'path2' are the same, and -1/1 if the file
    element for a file with pathname 'path1' would appear earlier/later in
    a music directory catalogue.

    Note: this method won't necessarily work properly if one or both of its
    arguments are pathnames of directories.
    """
    assert path1 is not None
    assert path2 is not None
    sep = os.sep
    comps1 = path1.split(sep)
    comps2 = path2.split(sep)
    n1 = len(comps1)
    n2 = len(comps2)
    result = 0
    if n1 == n2:
        for i in xrange(n1):
            result = cmp(comps1[i], comps2[i])
            if result != 0:
                break
    else:
        last1 = n1 - 1
        last2 = n2 - 1
        for i in xrange(min(n1, n2)):
            # All subdirs in a dir precede all files in the dir.
            isDir1 = (i < last1)
            isDir2 = (i < last2)
            if isDir1 and not isDir2:
                result = -1  # path1 < path2
            elif isDir2 and not isDir1:
                result = 1   # path1 > path2
            else:
                # The i'th components either both name dirs or both name
                # files.
                result = cmp(comps1[i], comps2[i])
            if result != 0:
                break
    assert abs(result) <= 1
    return result

def _fs_writeStartDirectoryCatalogueElement(w, path, numFiles, numSubdirs,
                                            indent = ""):
    """
    Writes out, using the file/stream object 'w', the start directory XML
    element that would appear in a music directory catalogue for a directory
    with (relative) pathname 'path' that contains 'numFiles' regular files
    and 'numSubdirs' direct subdirectories. Each line of the element will be
    prefixed with 'indent'.

    The last character output will be a newline.

    Note: this function takes care of quoting an escaping all values so that
    they're proper XML values.
    """
    assert w is not None
    assert path is not None
    assert numFiles >= 0
    assert numSubdirs >= 0
    assert indent is not None
    _fs_writeDirectoryCatalogueElement(w, _fs_startDirFmt, path, numFiles,
                                       numSubdirs, indent)

def _fs_writeEndDirectoryCatalogueElement(w, path, numFiles, numSubdirs,
                                            indent = ""):
    """
    Writes out, using the file/stream object 'w', the end directory XML
    element that would appear in a music directory catalogue for a directory
    with (relative) pathname 'path' that contains 'numFiles' regular files
    and 'numSubdirs' direct subdirectories. Each line of the element will be
    prefixed with 'indent'.

    The last character output will be a newline.

    Note: this function takes care of quoting an escaping all values so that
    they're proper XML values.
    """
    assert w is not None
    assert path is not None
    assert numFiles >= 0
    assert numSubdirs >= 0
    assert indent is not None
    _fs_writeDirectoryCatalogueElement(w, _fs_endDirFmt, path, numFiles,
                                       numSubdirs, indent)

def _fs_writeDirectoryCatalogueElement(w, fmt, path, numFiles, numSubdirs,
                                       indent = ""):
    """
    Writes out, using the file/stream object 'w', a directory XML element
    that would appear in a music directory catalogue for a directory with
    (relative) pathname 'path' that contains 'numFiles' regular files and
    'numSubdirs' direct subdirectories. Each line of the element will be
    prefixed with 'indent'.

    The element is built using the format 'fmt'.

    Note: this function takes care of quoting an escaping all values so that
    they're proper XML values.
    """
    assert w is not None
    assert fmt is not None
    assert path is not None
    assert numFiles >= 0
    assert numSubdirs >= 0
    assert indent is not None
    w.write(fmt % {
        "pathname": ut.ut_quoteForXml(path),
        "num-files": numFiles,
        "num-subdirs": numSubdirs,
        "indent": indent
    })

def _fs_fileCatalogueElementStart(path, mtime, indent = ""):
    """
    Returns a string containing the first line of a file XML element that
    would appear in a music directory catalogue for a music file with
    (relative) pathname 'path' and last modified time 'mtime'. The line
    will be prefixed with 'indent'. 'mtime' will be converted to an 'int'
    id it isn't already.

    The last character in the result will NOT be a newline.

    Note: this function takes care of quoting an escaping all values so that
    they're proper XML values.
    """
    #debug("---> in function musicfs._fs_fileCatalogueElementStart(%s, %s, %s)" % (path, str(mtime), indent))
    assert path is not None
    assert indent is not None
    result = _fs_fileStartFmt % {
        "pathname": ut.ut_quoteForXml(path),
        "mtime": int(mtime),
        "indent": indent
    }
    assert result
    return result

def _fs_fileCatalogueElementEnd(indent = ""):
    """
    Returns a string containing the last line of a file XML element that
    would appear in a music directory catalogue for a music file. The line
    will be prefixed with 'indent'.

    The last character in the result will be a newline.

    Note: this function takes care of quoting an escaping all values so that
    they're proper XML values.
    """
    assert indent is not None
    result = _fs_fileEndFmt % { "indent": indent }
    assert result
    return result

def _fs_appendFileCategoryCatalogueLines(lines, catName, itemMap, indent):
    """
    Appends lines to 'lines' that represent the category grandchild element
    of a file element for the category named 'catName' in a music directory
    catalogue, where the category contains items in the item name-value map
    'itemMap'.

    Note: no lines will be appended to 'lines' iff 'itemMap' is empty.

    Each line that this method appends to 'lines' will be prefixed with
    'indent'.
    """
    #debug("---> in function _fs_appendFileCategoryCatalogueLines(lines, %s, itemMap, %s)" % (catName, indent))
    assert lines is not None
    assert catName is not None
    assert itemMap is not None
    assert indent is not None
    if itemMap:
        #debug("    itemMap isn't empty")
        lines.append(_fs_categoryStartFmt %
                        { "indent": indent, "name": catName })
        in2 = indent + _fs_oneCatalogueIndentLevel

        # We sort the key-value pairs by the keys so that the pairs are
        # written out in a consistent order. We're not especially
        # concerned with what that order is, though.
        #debug("    sorting items by key ...")
        items = itemMap.items()
        ut.ut_sortTuplesByItem(items, 0)
        #debug("    appending lines for each item:")
        quote = ut.ut_quoteForXml
        for (k, v) in items:
            #debug("        key = [%s], value = [%s]" % (k, v))
            (ek, ev) = (quote(k), quote(v))
            #debug("        quoted: key = [%s], value = [%s]" % (ek, ev))
            lines.append(_fs_categoryItemFmt % { "indent": in2,
                                                 "name": ek, "value": ev })
        #debug("    appending element end line")
        lines.append(_fs_categoryEndFmt % { "indent": indent })
        #debug("    done")

def fs_parseRatingsFileLine(line):
    """
    Parses the line 'line' from a ratings file, returning a (rating, path)
    tuple if 'line' specifies a file's rating (where 'rating' is an int), and
    (None, line) if it is a comment line, and (None, None) if it is invalid.
    """
    assert line is not None
    strLine = line.strip()
    if strLine.startswith(_fs_ratingsFileCommentStart):
        result = (None, line)
    else:
        result = (None, None)
        parts = line.split(None, 1)
        try:
            if len(parts) == 2:
                result = (int(parts[0]), parts[1].strip())
        except:
            assert result == (None, None)
    assert len(result) == 2
    return result

def _fs_buildRatingsFileLine(rating, path, addNewline = False):
    """
    Builds and returns a line in a ratings file with rating 'rating' and
    path 'path'. The returned line will end in a newline iff 'addNewline'
    is True.
    """
    assert rating >= 0
    assert path is not None
    fmt = _fs_ratingsFileLineFmt
    if addNewline:
        fmt += "\n"
    result = fmt % { "path": path, "rating": rating }
    assert result is not None
    return result

def _fs_sendChangeRatingsCommand(cmd):
    """
    Sends the command 'cmd' to the change ratings daemon, returning True iff
    it was successfully sent.
    """
    assert cmd
    dest = fs_changeRatingCommandSink()
    if os.path.exists(dest):
        return ut.ut_sendCommandToFifo(cmd, dest)
    else:
        #raise IOError("Change ratings command sink '%s' doesn't exist" % dest)
        return False


def fs_defaultRatingToChancesConverter(rating):
    """
    Performs the default conversion of a music file's rating to the number
    of chances it has to be selected to appear in a playlist: a file has a
    number of chances equal to its rating.

    Thus files with a zero rating have no chance, and a file with rating 5
    has 5 times as many chances as does one with rating 1.
    """
    assert rating >= 0
    result = rating
    assert result >= 0
    return result

def fs_plusOneRatingToChancesConverter(rating):
    """
    Converts a music file's rating to a number of chances of being selected
    equal to its default number of chances plus one (where the default is
    determined by the fs_defaultRatingToChancesConverter() function).

    Thus files with rating 1 have twice as many chances as a file with rating
    zero, and a file with rating 5 has 3 times as many chances as one with
    rating 1 (since 3 = (5 + 1) / (1 + 1)).

    See fs_defaultRatingToChancesConverter().
    """
    assert rating >= 0
    result = fs_defaultRatingToChancesConverter(rating) + 1
    assert result >= 0
    return result

def fs_equalRatingToChancesConverter(rating):
    """
    Converts a music file's rating to exactly one chance of being selected,
    regardless of what the file's rating is, thus giving all files the same
    chance to be selected.

    Thus files with a zero rating have one chance, as do files with rating 5
    and rating 1 (or any other rating).
    """
    assert rating >= 0
    result = 1
    assert result >= 0
    return result

def fs_equalIfNonzeroRatingToChancesConverter(rating):
    """
    Converts a music file's rating to zero chances if it has rating 0, and to
    exactly one chance otherwise, thus giving all files with non-zero ratings
    the same chance to be selected.

    Thus files with a zero rating have no chances, and files with rating 5 or
    rating 1 (or any other non-zero rating) have one chance.
    """
    assert rating >= 0
    if rating > 0:
        result = 1
    else:
        result = 0
    assert result >= 0
    return result

def fs_minimumRatingToChancesConverter(rating, minRating):
    """
    Converts a music file's rating to zero chances if it has a rating less
    than 'minRating', and to rating 'rating - minRating + 1' otherwise, thus
    giving only music files whose ratings are at least 'minRating' any chance
    of being selected.

    Thus files with a rating less than 'minRating' have no chance, and a file
    with rating 5 above 'minRating' has 5 times as many chances as does one
    with rating 'minRating'.

    Note: this function takes two arguments rather than the one argument that
    rating-to-chances converter functions can take, so it is often used as
    part of a lambda expression to build a final rating-to-chances function.
    """
    assert rating >= 0
    assert minRating >= 0
    assert minRating <= config.maxRating
    result = max(rating - minRating + 1, 0)
    assert result >= 0
    return result


# Classes.

class fs_AbstractSortedMusicDirectoryCatalogueBuilder(object):
    """
    An abstract base class for classes of objects that build a music
    directory catalogue file whose 'file' elements are sorted in pathname
    order.

    Subclasses just have to override _fs_buildDirectoryTree().
    """

    def __init__(self, baseDir, errorOut = None):
        """
        Intializes us with the pathname 'baseDir' of the directory to which
        all of the pathnames in the catalogue we're building will be
        relative, and the file/stream 'errorOut' to which to write
        information about any errors or potential problems encountered while
        building catalogues. (No such messages will be written if 'errorOut'
        is None.)
        """
        assert baseDir is not None
        assert os.path.isabs(baseDir)
        # 'errorOut' may be None
        object.__init__(self)
        self._fs_baseDir = baseDir
        self._fs_errorWriter = errorOut
        self._fs_tmpDir = None

    def build(self, w):
        """
        Builds an XML document that is written out using the file/stream 'w'
        and that contains most of the useful information about each of the
        music files under the music directory we're cataloguing. Directories
        are not themselves catalogued. The XML elements that describe
        individual music files will appear in the catalogue XML document in
        pathname order.

        See _fs_buildDocument().
        """
        #debug("---> in fs_AbstractSortedMusicDirectoryCatalogueBuilder.build()")
        try:
            self._fs_buildDocument(w)
            #debug("    successfully built catalogue")
        except:
            #debug("*** BUILDING CATALOGUE DOCUMENT FAILED: %s" % ut.ut_exceptionDescription())
            raise
        #debug("   at end of fs_AbstractSortedMusicDirectoryCatalogueBuilder.build()")

    def _fs_buildDocument(self, w):
        """
        Builds an XML document that is written out using the file/stream 'w'
        and that contains most of the useful information about each of the
        music files under the music directory we're cataloguing. Directories
        are not themselves catalogued. The XML elements that describe
        individual music files will appear in the catalogue XML document in
        pathname order.

        See build().
        """
        #debug("---> in _fs_buildDocument()")
        assert w is not None
        assert self._fs_tmpDir == None
        tmpDir = None
        try:
            #debug("    creating temp dir ...")
            tmpDir = ut.ut_createTemporaryDirectory(_conf.tempDir,
                                        _fs_tempCatalogueDirPrefix)
            #debug("    created temp dir [%s]" % tmpDir)
            self._fs_tmpDir = tmpDir
            #debug("    building directory tree ...")
            self._fs_buildDirectoryTree()
            #debug("    converting tree to document")
            self._fs_convertDirectoryTreeToDocument(w)
            #debug("    conversion successful")
        finally:
            self._fs_tmpDir = None
            if tmpDir is not None:
                #debug("    deleting temp dir and everything under it")
                ut.ut_deleteTree(tmpDir)

    def _fs_buildDirectoryTree(self):
        """
        Builds a directory tree under our temporary directory from which a
        music directory catalogue file is to be built.
        """
        raise NotImplementedError


    def _fs_isExcludedNonMetadataDir(self, path):
        """
        Returns True iff the directory with pathname 'path' and everything
        under it should be excluded from the catalogue we're building, where
        'path' is assumed to not be under a metadata directory.
        """
        assert path is not None
        result = os.path.samefile(path, _conf.otherDir)
        return result

    def _fs_appendFileMetadataLines(self, lines, metaRoot, indent):
        """
        Appends lines to 'lines' that represent the metadata child element of
        a file element, where 'metaRoot' is the root pathname of all of the
        metadata files that describe the non-metadata file.

        Each line that this method appends to 'lines' will be prefixed with
        'indent'.
        """
        assert lines is not None
        assert metaRoot is not None
        assert indent is not None
        ext = _fs_originsMetadataFileExtension
        originsFile = mergedfs.fs_toFilesMetadataFilename(metaRoot, ext)
        ext = fs_tagsMetadataFileExtension
        tagsFile = mergedfs.fs_toFilesMetadataFilename(metaRoot, ext)
        ext = _fs_derivedMetadataFileExtension
        derivedFile = mergedfs.fs_toFilesMetadataFilename(metaRoot, ext)
        origLines = ut.ut_readFileLines(originsFile)
        tagLines = ut.ut_readFileLines(tagsFile)
        derivedLines = ut.ut_readFileLines(derivedFile)
        if origLines or tagLines or derivedLines:
            lines.append(_fs_metadataStartFmt % { "indent": indent })
            in2 = indent + _fs_oneCatalogueIndentLevel
            bd = self._fs_baseDirectory()
            rem = ut.ut_removePathnamePrefix
            m = mergedfs.fs_parseMetadataTagFileContents(origLines)
            m = dict([(k, rem(v, bd, v)) for (k, v) in m.items()])
                # removes our base dir from the start of origin pathnames
            _fs_appendFileCategoryCatalogueLines(lines,
                _fs_originsMetadataCategoryName, m, in2)
            m = mergedfs.fs_parseMetadataTagFileContents(tagLines)
            _fs_appendFileCategoryCatalogueLines(lines,
                _fs_tagsMetadataCategoryName, m, in2)
            m = mergedfs.fs_parseMetadataTagFileContents(derivedLines)
            _fs_appendFileCategoryCatalogueLines(lines,
                _fs_derivedMetadataCategoryName, m, in2)
            lines.append(_fs_metadataEndFmt % { "indent": indent })

    def _fs_writeRealFileDirectoryTreeFile(self, path, relPath):
        """
        Writes out the directory tree file for the "real" (album or track)
        audio file whose absolute and relative pathnames are 'path' and 'relPath',
        respectively.

        Note: the fact that the audio file really exists (as opposed to being
        created on demand by one of our filesystems) means that we can (and
        do) assume that there's no origins information to include in the
        directory tree file we write.
        """
        #debug("---> in _fs_writeRealFileDirectoryTreeFile(%s, %s)" % (path, relPath))
        assert path is not None
        assert os.path.isabs(path)
        assert relPath is not None
        assert not os.path.isabs(relPath)
        indent = _fs_fileElementIndent
        #debug("    indent: [%s]" % indent)
        mtime = _fs_cataloguedFileLastModifiedTime(path)
        #debug("    mtime = %s" % str(mtime))
        lines = []
        lines.append(_fs_fileCatalogueElementStart(relPath, mtime, indent))
        #debug("    building tags map")
        m = music.mu_tagsMap(path)
        #debug("    built tags map")
        if m:
            #debug("    tags map is non-empty")
            in2 = indent + _fs_oneCatalogueIndentLevel
            in3 = in2 + _fs_oneCatalogueIndentLevel
            lines.append(_fs_metadataStartFmt % { "indent": in2 })
            _fs_appendFileCategoryCatalogueLines(lines,
                    _fs_tagsMetadataCategoryName, m, in3)
            m = _fs_buildDerivedMetadataMap(music.mu_durationInSeconds(path))
            _fs_appendFileCategoryCatalogueLines(lines,
                    _fs_derivedMetadataCategoryName, m, in3)
            lines.append(_fs_metadataEndFmt % { "indent": in2 })
        #debug("    adding element end")
        lines.append(_fs_fileCatalogueElementEnd(indent))
        #debug("    writing element lines to the file [%s]" % relPath)
        self._fs_writeFileElementFile(relPath, lines)
        #debug("    done writing")

    def _fs_writeFileElementFileFromContents(self, relPath, contents):
        """
        Writes out the file with pathname 'relPath' relative to our temporary
        directory that will contain the text 'contents' making up the text of
        a file element in a catalogue.
        """
        assert relPath is not None
        assert not os.path.isabs(relPath)
        assert contents is not None
        self._fs_writeFileElementFile(relPath, [contents])

    def _fs_writeFileElementFile(self, relPath, lines):
        """
        Writes out the file with pathname 'relPath' relative to our temporary
        directory that will contain the lines 'lines' making up the text of
        a file element in a catalogue.
        """
        assert relPath is not None
        assert not os.path.isabs(relPath)
        assert lines is not None
        path = self._fs_temporaryPathname(relPath)
        ut.ut_createDirectory(os.path.dirname(path))
        ut.ut_writeFileLines(path, lines)


    def _fs_convertDirectoryTreeToDocument(self, w):
        """
        Converts the directory tree under our temporary directory into a
        music directory catalogue file that is written out using the
        file/stream object 'w'.
        """
        #debug("---> in _fs_convertDirectoryTreeToDocument()")
        assert w is not None
        w.write(_fs_xmlHeaderFmt)
        w.write(_fs_catalogueStartFmt % \
                    { "baseDir": self._fs_baseDirectory() })
        self._fs_convertSubdirectoryToFileElements('', w)
        w.write(_fs_catalogueEndFmt)

    def _fs_convertSubdirectoryToFileElements(self, relPath, w):
        """
        Converts the subdirectory of our temporary directory (or our
        temporary directory itself) with relative pathname 'relPath' into
        music directory catalogue file (and directory) elements that are
        then written out using the file/stream object 'w'.

        Note: 'relPath' is the empty string when we're processing our
        temporary directory, and non-empty if we're processing one of its
        subdirectories.
        """
        #debug("---> in _fs_convertSubdirectoryToFileElements(%s, w)" % relPath)
        assert relPath is not None
        assert w is not None
        dirs = []
        files = []
        fullPath = self._fs_temporaryPathname(relPath)
        for f in os.listdir(fullPath):
            p = os.path.join(fullPath, f)
            rp = os.path.join(relPath, f)
            if os.path.isdir(p):
                dirs.append(rp)
            else:
                files.append(p)  # not 'rp'
        if relPath:
            #debug("    writing dir start element for [%s]" % relPath)
            numFiles = len(files)
            numSubdirs = len(dirs)
            indent = _fs_oneCatalogueIndentLevel
            _fs_writeStartDirectoryCatalogueElement(w, relPath, numFiles,
                                                    numSubdirs, indent)

        # Convert all subdirectories, then all files.
        #debug("    sorting %i subdirs, %i files" % (len(dirs), len(files)))
        dirs.sort()
        files.sort()
        for rp in dirs:
            #debug("    converting subdir [%s]" % rp)
            self._fs_convertSubdirectoryToFileElements(rp, w)
        for p in files:
            #debug("    converting file with full pathname [%s]" % p)
            lines = ut.ut_readFileLines(p)
            if lines:
                # Note: the last line in 'lines' should already end with a
                # newline: see _fs_fileEndFmt.
                w.write("\n".join(lines))
            else:
                #debug("    error occurred")
                self._fs_reportError("failed to build the file element for "
                                     "the music file with pathname '%s'" % p)
        if relPath:
            #debug("    writing dir end element for [%s]" % relPath)
            _fs_writeEndDirectoryCatalogueElement(w, relPath, numFiles,
                                                  numSubdirs, indent)


    def _fs_temporaryDirectory(self):
        """
        Returns the pathname of our temporary directory: the directory under
        which we build our directory tree.

        See _fs_temporaryPathname().
        """
        result = self._fs_tmpDir
        assert result is not None
        return result

    def _fs_temporaryPathname(self, relPath):
        """
        Returns the pathname of the file under our temporary directory that
        corresponds to the file with relative pathname 'relPath' relative to
        our base directory.
        """
        assert relPath is not None
        assert not os.path.isabs(relPath)
        result = os.path.join(self._fs_temporaryDirectory(), relPath)
        assert result is not None
        return result

    def _fs_baseDirectory(self):
        """
        Returns the pathname of the directory to which all of the pathnames
        in the catalogue we're building will be relative.
        """
        result = self._fs_baseDir
        assert result is not None
        #assert os.path.isabs(result)
        return result

    def _fs_reportError(self, msg):
        """
        Reports an error described by the message 'msg', iff we're reporting
        errors.
        """
        w = self._fs_writer
        if w is not None:
            w.write("%s\n" % msg)

class fs_SortedMusicDirectoryCatalogueBuilder(fs_AbstractSortedMusicDirectoryCatalogueBuilder):
    """
    Represents objects that build a music directory catalogue file whose
    'file' elements are sorted in pathname order, where information about the
    music files is obtained from their corresponding metadata files if and
    when they exist, and from the music files themselves otherwise.
    """

    def __init__(self, topMusicDir, baseDir, errorOut = None):
        """
        Intializes us with the pathname 'baseDir' of the directory to which
        all of the pathnames in the catalogue we're building will be
        relative, the pathname 'topMusicDir' of the directory under which
        are found all of the music files that are to be catalogued, and the
        file/stream 'errorOut' to which to write information about any
        errors or potential problems encountered while building catalogues.
        (No such messages will be written if 'errorOut' is None.)
        """
        assert topMusicDir is not None
        assert baseDir is not None
        # 'errorOut' may be None
        fs_AbstractSortedMusicDirectoryCatalogueBuilder. \
            __init__(self, baseDir, errorOut)
        self._fs_topMusicDir = topMusicDir

    def build(self, w):
        #debug("---> in fs_SortedMusicDirectoryCatalogueBuilder.build()")
        assert w is not None
        if os.path.isdir(self._fs_topMusicDir):
            #debug("    top music dir [%s] is indeed a directory" % self._fs_topMusicDir)
            fs_AbstractSortedMusicDirectoryCatalogueBuilder.build(self, w)
        #debug("    at end of fs_SortedMusicDirectoryCatalogueBuilder.build()")

    def _fs_buildDirectoryTree(self):
        topDir = self._fs_topMusicDir
        metaDir = mergedfs.fs_findFilesMetadataSubdirectoryIn(topDir)
        if metaDir is not None:
            for f in os.listdir(metaDir):
                p = os.path.join(metaDir, f)
                self._fs_buildMetadataDirectoryTreePartFor(p, f)
        else:
            for f in os.listdir(topDir):
                p = os.path.join(topDir, f)
                self._fs_buildDirectoryTreePartFor(p, f)


    def _fs_buildMetadataDirectoryTreePartFor(self, path, relPath):
        """
        Builds the part of the directory tree under our temporary directory
        that contains most of the useful information about the non-metadata
        files described by the metadata file with pathname 'path' and any and
        all metadata files under it (if it's a directory).

        'relPath' is the pathname relative to our base directory of the non-
        metadata file described by the metadata file with pathname 'path'.

        Note: 'path' will never be the pathname of the files metadata
        subdirectory itself: it will always be that of a file or directory
        under it.
        """
        assert path is not None
        assert relPath is not None
        assert not os.path.isabs(relPath)
        if os.path.isdir(path):
            for f in os.listdir(path):
                p = os.path.join(path, f)
                rp = os.path.join(relPath, f)
                self._fs_buildMetadataDirectoryTreePartFor(p, rp)
        elif mergedfs.fs_doesEndWithMetadataExtension(path, mergedfs.
                                             fs_pathnameMetadataFileExtension):
            # 'path' is the pathname of a pathname metadata file, but the
            # pathname that it contains is absolute, so we use 'relPath'
            # after removing the metadata extensions.
            origPath = mergedfs.fs_removeMetadataFileExtensions(relPath)
            mtime = _fs_cataloguedFileLastModifiedTime(path)
                # since a metadata file's timestamps are the same as those of the
                # file it describes (see mergedfs.fs_MetadataFileStat)
            lines = []
            indent = _fs_fileElementIndent
            lines.append(_fs_fileCatalogueElementStart(origPath,
                                                       mtime, indent))
            metaRoot = mergedfs.fs_removeMetadataFileExtensions(path)
            newIndent = indent + _fs_oneCatalogueIndentLevel
            self._fs_appendFileMetadataLines(lines, metaRoot, newIndent)
            lines.append(_fs_fileCatalogueElementEnd(indent))
            self._fs_writeFileElementFile(relPath, lines)

    def _fs_buildDirectoryTreePartFor(self, path, relPath):
        """
        Builds the part of the directory tree under our temporary directory
        that contains most of the useful information about the file with
        pathname 'path' if it isn't a directory, and about all of the files
        under the directory with pathname 'path' otherwise.

        'relPath' is 'path' relative to our base directory.
        """
        metaDir = mergedfs.fs_findFilesMetadataSubdirectoryIn(path)
        if self._fs_isExcludedNonMetadataDir(path):
            pass
        elif metaDir is not None:
            for f in os.listdir(metaDir):
                p = os.path.join(metaDir, f)
                rp = os.path.join(relPath, f)  # skip the metadata dir part
                self._fs_buildMetadataDirectoryTreePartFor(p, rp)
        elif os.path.isdir(path):
            # We don't catalogue directories, just files.
            for f in os.listdir(path):
                p = os.path.join(path, f)
                rp = os.path.join(relPath, f)
                self._fs_buildDirectoryTreePartFor(p, rp)
        elif os.path.exists(path) and music.mu_hasMusicFilename(path):
            # 'path' is pathname of a non-directory, non-metadata music file.
            # (The exists() check ensures we ignore broken links.)
            self._fs_writeRealFileDirectoryTreeFile(path, relPath)
        # We ignore files that aren't directories, metadata files or music files.

class fs_MergingSortedMusicDirectoryCatalogueBuilder(fs_AbstractSortedMusicDirectoryCatalogueBuilder):
    """
    Represents the class of fs_AbstractSortedMusicDirectoryCatalogueBuilder
    that builds a catalogue by merging together the information in one or
    more other catalogues.
    """

    def __init__(self, cataloguePaths, baseDir, errorOut = None):
        """
        Initializes us with the pathnames 'cataloguePaths' of the catalogue
        files that we're to merge into single catalogue, the pathname
        'baseDir' of the directory to which all of the pathnames in the
        catalogue we're building will be relative, and the file/stream
        'errorOut' to which to write information about any errors or
        potential problems encountered while building catalogues. (No such
        messages will be written if 'errorOut' is None.)

        Note: if more than on catalogue whose pathname is in 'cataloguePaths'
        contains information about a given music file then the information
        from the catalogue whose pathname appears nearest to the end of
        'cataloguePaths' will be what ends up in the merged catalogue that we
        build.
        """
        assert cataloguePaths  # isn't allowed to be empty
        assert baseDir is not None
        # 'errorOut' may be None
        fs_AbstractSortedMusicDirectoryCatalogueBuilder. \
            __init__(self, baseDir, errorOut)
        self._fs_catPaths = cataloguePaths

    def _fs_buildDirectoryTree(self):
        #debug("---> in fs_MergingSortedMusicDirectoryCatalogueBuilder._fs_buildDirectoryTree()")
        catPaths = self._fs_catPaths
        tmpDir = self._fs_temporaryDirectory()
        #debug("    building dir tree under [%s]" % tmpDir)
        for p in catPaths:
            #debug("    exploding catalogue [%s] into the dir tree" % p)
            fs_explodeMusicDirectoryCatalogue(p, tmpDir)

class fs_AbstractGenerateCatalogueDaemonProcess(ut.
    ut_AbstractOutputDaemonProcess, mergedfs.
    fs_GenerateFileDaemonProcessMixin):
    """
    An abstract base class for classes that represent daemon processes that
    generate a filesystem's catalogue summary metadata file.

    Subclasses just have to implement our _fs_catalogueBuilderFromGenerator()
    method.
    """

    def __init__(self, generator, wfd, tmpPath, finalPath, doClose = True):
        """
        Initializes us with the generator object 'generator', the file
        descriptor 'wfd' to write the generator's output to, the pathname
        'tmpPath' of the file we generate while we're generating it, and the
        pathname 'finalPath' that 'tmpPath' will be renamed to if/when it's
        fully and successfully generated.

        'wfd' will be closed when this process is done with it iff 'doClose'
        is True.

        Initializes us with the pathname 'tmpPath' of the file we generate
        while we're generating it, and the pathname 'finalPath' that 'tmpPath'
        will be renamed to if/when it's fully and successfully generated.
        """
        #debug("---> in fs_AbstractGenerateCatalogueDaemonProcess.__init__(generator, %s, %s, %s, doClose = %s)" % (str(wfd), tmpPath, finalPath, str(doClose)))
        assert generator is not None
        assert wfd is not None
        assert tmpPath is not None
        assert finalPath is not None

        # Note: the order of the following '__init__()' calls is EXTREMELY
        # important since ut_AbstractOutputDaemonProcess.__init__() causes
        # the daemon process to be forked.
        #debug("    calling fs_GenerateFileDaemonProcessMixin.__init__() ...")
        mergedfs.fs_GenerateFileDaemonProcessMixin.__init__(self, tmpPath,
                                                            finalPath)
        #debug("    calling ut_AbstractOutputDaemonProcess.__init__() ...")
        ut.ut_AbstractOutputDaemonProcess.__init__(self, generator,
                                                   wfd, doClose = doClose)

    def _fs_generateTemporaryFile(self, path):
        #debug("---> in _fs_GenerateCatalogueDaemonProcess._fs_generateTemporaryFile(%s)" % path)
        assert path is not None
        ut.ut_AbstractOutputDaemonProcess._ut_run(self)

    def _ut_run(self):
        #debug("---> in _fs_GenerateCatalogueDaemonProcess._ut_run()")
        self._ut_reallyRun()

    def _ut_writeOutput(self, generator, wfd, bufSize):
        #debug("---> in fs_AbstractGenerateCatalogueDaemonProcess._ut_writeOutput()")
        assert generator is not None
        assert wfd is not None
        assert bufSize > 0
        w2 = None
        try:
            #debug("    opening writable file on 'wfd' file descriptor ...")
            #w1 = os.fdopen(wfd, 'w', bufSize)
            #debug("    opening temp file (for writing) ...")
            #w2 = file(self._fs_temporaryFile(), 'w', bufSize)
            #debug("    creating ut_MultiplexedWritableStream from the 2 files ...")
            #w = ut.ut_MultiplexedWritableStream(w2, w1)
            #w.setDebugFunction(debug)
# TODO: REPLACE THE FOLLOWING LINES with the commented out ones above !!!
# - after uncommenting them and fixing them:
# - for some reason writing to 'w1' (wrapping 'wfd') blocks when we get 65536
#   bytes into the output: figure out why
# - for now we just don't write to 'wfd'/'w1', which is fine for now since it
#   isn't currently read, but if/when it is used in the future then we'll be in
#   trouble
            #debug("    opening temp file (for writing) ...")
            w = file(self._fs_temporaryFile(), 'w', bufSize)

            #debug("    getting catalogue builder from generator ...")
            b = self._fs_catalogueBuilderFromGenerator(generator)
            #debug("    starting to build the catalogue ...")
            try:
                b.build(w)
            except:
                #debug("    *** CATALOGUE BUILD FAILED: %s" % ut.ut_exceptionDescription())
                raise
            #debug("    ... done building the catalogue")
        finally:
            # We intentionally don't close 'w1' here since that would close
            # 'wfd' too (at least if os.fdopen() works the same way that the
            # corresponding C function does and doesn't dup 'wfd').
            #debug("    closing the catalogue temp file")
            if w2 is not None:
                w2.close()

    def _fs_catalogueBuilderFromGenerator(self, generator):
        """
        Given the generator object 'generator' that we were constructed
        from, returns the fs_AbstractSortedMusicDirectoryCatalogueBuilder
        subclass instance that we're to use to build our catalogue.

        Note: usually 'generator' contains (or is) the catalogue builder.
        """
        assert generator is not None
        raise NotImplementedError
        #assert result is not None

class fs_DefaultGenerateCatalogueDaemonProcess(fs_AbstractGenerateCatalogueDaemonProcess):
    """
    The default class that represents daemon processes that generate a
    filesystem's catalogue summary metadata file: its generator is an
    instance of an fs_AbstractSortedMusicDirectoryCatalogueBuilder subclass.
    """

    def _fs_catalogueBuilderFromGenerator(self, generator):
        assert generator is not None
        result = generator
        assert result is not None
        return result


class _fs_AbstractCataloguedFileInformation(object):
    """
    An abstract base class for classes that contain information from the
    entry for a single file or directory in a music directory catalogue.
    """

    def fs_setPathname(self, value):
        """
        Sets our file's (relative) pathname to 'value'.
        """
        assert value is not None
        self._fs_pathname = value

    def fs_pathname(self):
        """
        Returns our file's (relative) pathname.
        """
        result = self._fs_pathname
        assert result is not None
        return result

class fs_CataloguedDirectoryInformation(_fs_AbstractCataloguedFileInformation):
    """
    Contains the information from the entry for a single directory in a
    music directory catalogue.
    """

    def fs_setFileCount(self, n):
        """
        Sets to 'n' the number of files that our directory contains directly
        (that is, not counting any under any subdirectories).
        """
        assert n >= 0
        self._fs_fileCount = n

    def fs_fileCount(self):
        """
        Returns the number of files that our directory contains directly.
        """
        result = self._fs_fileCount
        assert result >= 0
        return result

    def fs_setSubdirectoryCount(self, n):
        """
        Sets to 'n' the number of subdirectories our directory contains
        directly (that is, not counting any under other subdirectories).
        """
        assert n >= 0
        self._fs_subdirCount = n

    def fs_subdirectoryCount(self):
        """
        Returns the number of subdirectories that our directory contains
        directly.
        """
        result = self._fs_subdirCount
        assert result >= 0
        return result

    def writeStartXmlElement(self, w):
        """
        Writes out, using the file/stream object 'w', the text of the
        directory start XML catalogue element whose information we contain.
        """
        assert w is not None
        _fs_writeStartDirectoryCatalogueElement(w, self.fs_pathname(),
                        self.fs_fileCount(), self.fs_subdirectoryCount())

    def writeEndXmlElement(self, w):
        """
        Writes out, using the file/stream object 'w', the text of the
        directory end catalogue XML element whose information we contain.
        """
        assert w is not None
        _fs_writeEndDirectoryCatalogueElement(w, self.fs_pathname(),
                        self.fs_fileCount(), self.fs_subdirectoryCount())

class fs_CataloguedFileInformation(_fs_AbstractCataloguedFileInformation):
    """
    Contains the information from the entry for a single file in a music
    directory catalogue.
    """

    def __init__(self):
        _fs_AbstractCataloguedFileInformation.__init__(self)
        self._fs_categoryMap = {}
            # maps each category name to a map that maps the name of each
            # item in that category to its value.

    def fs_setLastModifiedTime(self, value):
        """
        Sets our file's last modified date/time to 'value', where 'value' is
        assumed to be an int.
        """
        assert value >= 0
        self._fs_mtime = value

    def fs_lastModifiedTime(self):
        """
        Returns our file's last modified date/time as an int.
        """
        result = self._fs_mtime
        assert result >= 0
        return result

    def fs_realOriginalFilePathname(self):
        """
        Returns the (relative) pathname of the "real" file that we're just
        a mirror of, or None if we're not a mirror of a "real" file.
        """
        result = self.fs_originsValue(fs_realOriginalOriginsTagName)
        # 'result 'may be None
        return result

    def fs_isOriginalFile(self):
        """
        Returns True iff our file is an original file: that is, iff it's not
        just a reencoding of another file.

        See fs_originalFilePathname().
        """
        return self.fs_originalFilePathname() is None

    def fs_originalFilePathname(self):
        """
        Returns the (relative) pathname of the file that we're just a
        reencoding of, or None if we're an original file.

        Note: the result, if not None, is relative to the same directory
        as is the result of calling fs_pathname().

        See fs_isOriginalFile().
        """
        result = self.fs_originsValue(fs_originalOriginsTagName)
        # 'result' may be None
        return result

    def fs_originalFilePathnameOrPathname(self, path = None):
        """
        Returns the result of 'fs_originalFilePathname()' if it's not None;
        otherwise it returns 'path' if that's not None, and the result of
        calling fs_pathname() if 'path' is None.
        """
        result = self.fs_originalFilePathname()
        if result is None:
            result = path
            if result is None:
                result = self.fs_pathname()
        assert result is not None
        return result

    def fs_durationInSeconds(self):
        """
        Returns the duration of the audio content in our file, or None if its
        duration could not be determined.
        """
        result = self.fs_derivedValue(fs_durationInSecondsDerivedTagName)
        # 'result' may be None
        return result


    def fs_addCategoryItem(self, categoryName, itemName, itemValue):
        """
        Adds a category item named 'itemName' with value 'itemValue'
        to our file's metadata category named 'categoryName'.
        """
        assert categoryName is not None
        assert itemName is not None
        assert itemValue is not None
        m = self._fs_categoryMap
        itemMap = m.get(categoryName)
        if itemMap is None:
            itemMap = {}
            m[categoryName] = itemMap
        itemMap[itemName] = itemValue

    def fs_removeAllCategoryItems(self, categoryName):
        """
        Removes any and all items in our file's metadata category named
        'categoryName'.
        """
        assert categoryName is not None
        try:
            del self._fs_categoryMap[categoryName]
        except KeyError:
            pass  # we don't have any items in the named category

    def fs_tagValue(self, itemName):
        """
        Returns the value of the item named 'itemName' in the tags category
        in our file's metadata, or returns None if there is no such item in
        that category for our file.
        """
        assert itemName is not None
        # 'result' may be None
        return self.fs_categoryItemValue(_fs_tagsMetadataCategoryName,
                                         itemName)

    def fs_originsValue(self, itemName):
        """
        Returns the value of the item named 'itemName' in the origins
        category in our file's metadata, or returns None if there is no such
        item in that category for our file.
        """
        assert itemName is not None
        # 'result' may be None
        return self.fs_categoryItemValue(_fs_originsMetadataCategoryName,
                                         itemName)

    def fs_derivedValue(self, itemName):
        """
        Returns the value of the item named 'itemName' in the derived
        category in our file's metadata, or returns None if there is no such
        item in that category for our file.
        """
        assert itemName is not None
        # 'result' may be None
        return self.fs_categoryItemValue(_fs_derivedMetadataCategoryName,
                                         itemName)

    def fs_categoryItemValue(self, categoryName, itemName):
        """
        Returns the value of the item named 'itemName' in the category
        named 'categoryName' in our file's metadata, or returns None if
        there is no such item and/or category for our file.
        """
        assert categoryName is not None
        assert itemName is not None
        result = None
        itemMap = self._fs_categoryMap.get(categoryName)
        if itemMap is not None:
            result = itemMap.get(itemName)
        # 'result' may be None
        return result

    def writeXmlElement(self, w):
        """
        Writes out, using the file/stream object 'w', the text of the file
        catalogue XML element whose information we contain.

        Note: the last line will end with a newline.
        """
        assert w is not None
        indent = _fs_fileElementIndent
        lines = []
        lines.append(_fs_fileCatalogueElementStart(self.fs_pathname(),
                                        self.fs_lastModifiedTime(), indent))
        catMap = self._fs_categoryMap
        if catMap:
            in2 = indent + _fs_oneCatalogueIndentLevel
            in3 = in2 + _fs_oneCatalogueIndentLevel
            lines.append(_fs_metadataStartFmt % { "indent": in2 })
            catNames = [_fs_originsMetadataCategoryName,
                        _fs_tagsMetadataCategoryName,
                        _fs_derivedMetadataCategoryName]
            for name in catNames:
                _fs_appendFileCategoryCatalogueLines(lines, name,
                    catMap.get(name, {}), in3)
            lines.append(_fs_metadataEndFmt % { "indent": in2 })
        lines.append(_fs_fileCatalogueElementEnd(indent))
        for line in lines:
            w.write(line)
            w.write("\n")

class _fs_CatalogueParserErrorHandler(xml.sax.ErrorHandler):
    """
    The class of error handler used to handle errors that occur when parsing
    a music directory catalogue.
    """
    def fatalError(self, exception):
        if str(exception).endswith(": no element found"):
            (value, type, traceback) = sys.exc_info()
            warn("Caught and ignored a possibly spurious 'no element " +
                 "found' error when parsing a catalogue file: %s\n%s" %
                 (value, traceback))
        else:
            xml.sax.ErrorHandler.fatalError(self, exception)

class fs_AbstractMusicDirectoryCatalogueParser(xml.sax.ContentHandler):
    """
    An abstract base class for classes that parse a music directory catalogue
    file.

    Note: the file elements in a music directory catalogue are sorted in
    pathname order.

    See fs_SortedMusicDirectoryCatalogueBuilder.
    """

    def __init__(self):
        xml.sax.ContentHandler.__init__(self)
        self._fs_baseDir = None
        self._fs_currFileInfo = None
        self._fs_currCategoryName = None
        self._fs_currCategoryItemName = None
        self._fs_currContent = None

    def fs_parse(self, catalogue):
        """
        Parses the music directory catalogue file with pathname 'catalogue'.
        """
        #debug("---> in fs_AbstractMusicDirectoryCatalogueParser.fs_parse(%s)" % catalogue)
        assert catalogue is not None
        self._fs_beforeParsing()
        try:
            #debug("    about to parse catalogue ...")
            try:
                eh = _fs_CatalogueParserErrorHandler()
                ut.ut_saxParseXmlFile(catalogue, self, eh)
            except:
                #debug("    parsing catalogue failed: %s" % ut.ut_exceptionDescription())
                raise
            #debug("    done parsing catalogue")
        finally:
            #debug("    calling _fs_afterParsing() ...")
            self._fs_afterParsing()
            #debug("    _fs_afterParsing() returned")

    def _fs_catalogueBaseDirectory(self):
        """
        Returns the pathname of the base directory specified in the
        catalogue we're currently processing, or None if it hasn't been
        obtained yet.
        """
        result = self._fs_baseDir
        # 'result' may be None
        return result


    def characters(self, content):
        if self._fs_currContent is not None:
            # Then we're inside a category item's value.
            self._fs_currContent += content

    def startElement(self, name, attrs):
        if name == _fs_fileElementName:
            info = fs_CataloguedFileInformation()
            an = _fs_pathnameAttributeName
            info.fs_setPathname(attrs[an])
            an = _fs_lastModifiedTimeAttributeName
            info.fs_setLastModifiedTime(int(attrs[an]))
            self._fs_currFileInfo = info
        elif name == _fs_categoryElementName:
            an = _fs_categoryNameAttributeName
            self._fs_currCategoryName = attrs[an]
        elif name == _fs_categoryItemElementName:
            an = _fs_categoryItemNameAttributeName
            self._fs_currCategoryItemName = attrs[an]
            self._fs_currContent = ""  # ready to be appended to
        elif name == _fs_metadataElementName:
            pass # nothing to do here
        elif name == _fs_startDirElementName or \
             name == _fs_endDirElementName:
            info = fs_CataloguedDirectoryInformation()
            an = _fs_pathnameAttributeName
            info.fs_setPathname(attrs[an])
            an = _fs_fileCountAttributeName
            info.fs_setFileCount(int(attrs[an]))
            an = _fs_subdirCountAttributeName
            info.fs_setSubdirectoryCount(int(attrs[an]))
            if name == _fs_startDirElementName:
                self._fs_processDirectoryStartInformation(info)
            else:
                self._fs_processDirectoryEndInformation(info)
        else:
            assert name == _fs_catalogueElementName
                # otherwise we've found a type of element we don't know about
            self._fs_baseDir = attrs[_fs_baseDirAttributeName]
            self._fs_beforeParsing()

    def endElement(self, name):
        if name == _fs_fileElementName:
            self._fs_processFileInformation(self._fs_currFileInfo)
            self._fs_currFileInfo = None
        elif name == _fs_categoryElementName:
            self._fs_currCategoryName = None
            pass
        elif name == _fs_categoryItemElementName:
            info = self._fs_currFileInfo
            info.fs_addCategoryItem(self._fs_currCategoryName,
                self._fs_currCategoryItemName, self._fs_currContent)
            self._fs_currCategoryItemName = None
            self._fs_currContent = None
        elif name == _fs_metadataElementName:
            pass # nothing to do here
        elif name == _fs_startDirElementName or \
             name == _fs_endDirElementName:
            pass # nothing to do here
        else:
            assert name == _fs_catalogueElementName
                # otherwise we've found a type of element we don't know about


    def _fs_beforeParsing(self):
        """
        Performs any processing that there is to do before we start parsing
        the catalogue.
        """
        pass  # by default we do nothing here

    def _fs_processDirectoryStartInformation(self, info):
        """
        Processes the information obtained from the latest catalogue
        "directory start" element that we've just finished parsing. The
        fs_CataloguedDirectoryInformation object 'info' contains all of the
        information parsed out of the element.
        """
        assert info is not None
        pass  # by default we do nothing here

    def _fs_processDirectoryEndInformation(self, info):
        """
        Processes the information obtained from the latest catalogue
        "directory end" element that we've just finished parsing. The
        fs_CataloguedDirectoryInformation object 'info' contains all of the
        information parsed out of the element.
        """
        assert info is not None
        pass  # by default we do nothing here

    def _fs_processFileInformation(self, info):
        """
        Processes the information obtained from the latest catalogue file
        element that we've just finished parsing. The
        fs_CataloguedFileInformation object 'info' contains all of the
        information parsed out of the file element.

        Note: a catalogue's file elements are in pathname order, and so
        they will be processed by calls to this method in that order.
        """
        assert info is not None
        raise NotImplementedError

    def _fs_afterParsing(self):
        """
        Performs and processing that there is to do after we have finished
        parsing the entire catalogue.
        """
        pass  # by default we do nothing here

class fs_MusicDirectoryCatalogueExploder(fs_AbstractMusicDirectoryCatalogueParser):
    """
    A class that "explodes" a music directory catalogue into a directory full
    of files, where each file contains the catalogue's XML element that
    describes exactly one music file.

    This class performs the reverse of the operation that is performed by an
    fs_SortedMusicDirectoryCatalogueBuilder when it converts a directory of
    files into a music directory catalogue.

    See fs_explodeMusicDirectoryCatalogue().
    """

    def __init__(self, destDir):
        """
        Initializes us from the pathname of the directory under which to put
        the results of exploding the catalogue into individual files.
        """
        assert destDir is not None
        assert os.path.isabs(destDir)
        assert os.path.isdir(destDir)
        self._fs_destDir = destDir
        fs_AbstractMusicDirectoryCatalogueParser.__init__(self)

    def _fs_processDirectoryStartInformation(self, info):
        assert info is not None
        # Ensure that the corresponding directory under our dest dir
        # exists. (It's less work if we do it here rather than when
        # processing each file.)
        path = os.path.join(self._fs_destDir, info.fs_pathname())
        ut.ut_createDirectory(path)

    def _fs_processFileInformation(self, info):
        """
        Processes the information obtained from the latest catalogue file
        element that we've just finished parsing. The
        fs_CataloguedFileInformation object 'info' contains all of the
        information parsed out of the file element.

        Note: a catalogue's file elements are in pathname order, and so
        they will be processed by calls to this method in that order.
        """
        assert info is not None
        info = self._fs_transformFileInformation(info)
        if info is not None:
            path = os.path.join(self._fs_destDir, info.fs_pathname())
            ut.ut_createDirectory(os.path.dirname(path))
                # in case it doesn't already exist
            w = None
            try:
                w = file(path, 'w')
                info.writeXmlElement(w)
            finally:
                if w is not None:
                    w.close()

    def _fs_transformFileInformation(self, info):
        """
        Transforms the fs_CataloguedFileInformation 'info' that represents
        the latest catalogue file element we've just finished parsing before
        we explode it into a file element file. Returns the transformed
        information, or None if the file's information is to be omitted.

        This implementation returns 'info' unchanged.
        """
        assert info is not None
        # 'result' may be None
        return info

class fs_OrderedPathnameListBuilder(fs_AbstractMusicDirectoryCatalogueParser):
    """
    A class that builds and outputs a list of the pathnames of all of the
    music files in a subdirectory of a music directory given that music
    directory's catalogue.
    """

    def __init__(self, w, subdir = '', sep = '\n'):
        """
        Initializes the object with the file/stream object 'w' that it is to
        use to write out a list of the files under the music directory
        subdirectory with pathname 'subdir'. The pathnames in the file list
        will be separated by 'sep'.

        Note: the 'subdir' part will be omitted from the start of each
        pathname in the list. Iff 'subdir' is '' then all files in the music
        directory catalogue will be included in the list.
        """
        assert w is not None
        assert subdir is not None
        assert sep is not None
        fs_AbstractMusicDirectoryCatalogueParser.__init__(self)
        self._fs_writer = w
        self._fs_subdir = subdir
        self._fs_separator = sep

    def _fs_processFileInformation(self, info):
        """
        Processes the information obtained from the latest catalogue file
        element that we've just finished parsing. The
        fs_CataloguedFileInformation object 'info' contains all of the
        information parsed out of the file element.

        Note: a catalogue's file elements are in pathname order, and so
        they will be processed by calls to this method in that order.
        """
        assert info is not None
        if self._fs_doIncludeFile(info):
            p = self._fs_removeSubdirectoryPrefix(info.fs_pathname())
            self._fs_writeLinesFor(p, info)

    def _fs_removeSubdirectoryPrefix(self, path):
        """
        Returns the result of removing our subdirectory from the front of
        the pathname 'path', if it has it as a prefix: otherwise 'path' is
        returned unchanged.
        """
        assert path is not None
        result = ut.ut_removePathnamePrefix(path, self._fs_subdir)
        assert result is not None
        return result

    def _fs_originalFilePathnameOrPathname(self, info, path = None):
        """
        Returns 'info.fs_originalFilePathnameOrPathname(path)' with our
        subdirectory removed from the front of it if it has it as a prefix,
        """
        assert info is not None
        # 'path' may be None
        result = info.fs_originalFilePathnameOrPathname(path)
        result = self._fs_removeSubdirectoryPrefix(result)
        return result

    def _fs_write(self, txt):
        """
        Writes out the text 'txt': no separator is output after it.

        See _fs_writeLine().
        """
        self._fs_writer.write(txt)

    def _fs_writeLine(self, txt):
        """
        Writes the text 'txt' followed by our list separator (which is often
        a line terminator, hence the name of this method).
        """
        self._fs_write("%s%s" % (txt, self._fs_separator))


    def _fs_doIncludeFile(self, info):
        """
        Returns True iff the music file described by 'info' (a
        fs_CataloguedFileInformation object) is to be included in the file
        list.

        By default all files are included.
        """
        assert info is not None
        return ut.ut_hasPathnamePrefix(info.fs_pathname(), self._fs_subdir)

    def _fs_writeLinesFor(self, path, info):
        """
        Writes out the line(s) corresponding to the pathname 'path' to the
        file list that we build. The fs_CataloguedFileInformation 'info'
        describes the file with pathname 'path'.

        Note: 'path' is the same as info.fs_pathname() with our music
        directory subdirectory removed from the start of it.

        See _fs_writeLine().
        See _fs_write().
        """
        assert path is not None
        assert info is not None
        self._fs_writeLine(path)

class fs_OrderedOriginalPathnameListBuilder(fs_OrderedPathnameListBuilder):
    """
    A class that builds and outputs a list of the pathnames of all of the
    original music files in a given music directory catalogue.
    """

    def _fs_doIncludeFile(self, info):
        # Overrides version in fs_OrderedPathnameListBuilder.
        assert info is not None
        result = fs_OrderedPathnameListBuilder. \
                                    _fs_doIncludeFile(self, info) and \
            info.fs_isOriginalFile()
        return result

class fs_PathnameToOriginalPathnameMapBuilder(fs_AbstractMusicDirectoryCatalogueParser):
    """
    Represents classes that parse a music directory catalogue and for each
    music file in the catalogue adds a mapping to a map from the file's
    pathname to the pathname of its original file (which is the file's
    pathname itself if the file is an original file).

    Note: all of the pathnames in the map that's built - both keys and
    values - will be relative to the music directory that the catalogue
    catalogues. So for example a map built from the main music directory
    catalogue will contain pathnames that are relative to the root music
    directory.
    """

    def __init__(self, m):
        """
        Initializes us with the map to which we're to add mappings.
        """
        assert m is not None
        fs_AbstractMusicDirectoryCatalogueParser.__init__(self)
        self._fs_map = m

    def _fs_processFileInformation(self, info):
        assert info is not None
        path = info.fs_pathname()
        origPath = info.fs_originalFilePathnameOrPathname(path)

        # The str() calls convert Unicode strings to 'regular' ones, which
        # DBM files can deal with.
        self._fs_map[str(path)] = str(origPath)

class fs_PathnameToInformationMapBuilder(fs_AbstractMusicDirectoryCatalogueParser):
    """
    The class of catalogue parser that, for each music file in the catalogue,
    adds a mapping to a map from the file's pathname to an information object
    of class fs_CataloguedFileInformation that describes the file.

    Note: all of the pathnames that are keys into the map that's built will
    be relative to the music directory that the catalogue catalogues. So for
    example a map built from the main music directory catalogue will have
    keys that are pathnames that are relative to the root music directory.
    """
    def __init__(self, m):
        """
        Initializes us with the map to which we're to add mappings.
        """
        assert m is not None
        fs_AbstractMusicDirectoryCatalogueParser.__init__(self)
        self._fs_map = m

    def _fs_processFileInformation(self, info):
        assert info is not None
        path = info.fs_pathname()

        # The str() call converts Unicode strings to 'regular' ones, which
        # shelf files can deal with.
        self._fs_map[str(path)] = info

class fs_NewRatingsFileBuilder(fs_OrderedOriginalPathnameListBuilder):
    """
    Represents classes that parse a music directory catalogue in order to
    build a new ratings file from it.
    """

    def __init__(self, w, defaultRating, ratingsMap = None):
        """
        Initializes us with the file/stream object to use to write out the
        ratings file and the rating that every file is to have initially.

        If 'ratingsMap' is not None then for each file its original file's
        pathname is searched for in 'ratingsMap' and if it is mapped to a
        rating then that rating is used in place of 'defaultRating' for that
        file.
        """
        #debug("---> in fs_NewRatingsFileBuilder.__init__(w, %s, %s)" % (str(defaultRating), ut.ut_prettyShortMap(ratingsMap)))
        assert w is not None
        assert defaultRating >= 0
        # 'ratingsMap' may be None
        fs_OrderedOriginalPathnameListBuilder. \
            __init__(self, w, _conf.baseSubdir)
        self._fs_defaultRating = defaultRating
        self._fs_ratingsMap = ratingsMap

    def _fs_writeLinesFor(self, path, info):
        #debug("---> in fs_NewRatingsFileBuilder._fs_writeLinesFor(%s, info)" % path)
        assert path is not None
        assert info is not None
        rating = self._fs_defaultRating
        m = self._fs_ratingsMap
        if m is not None:
            #debug("    using ratings map in building new ratings file")
            origPath = self._fs_originalFilePathnameOrPathname(info)
            #debug("    default rating = %i, origPath = [%s]" % (rating, origPath))
            rating = _fs_findNewRating(m, origPath, rating)
            #debug("    final rating = %i" % rating)
        self._fs_writeLine(_fs_buildRatingsFileLine(rating, path))

class fs_UpdatedRatingsFileBuilder(fs_OrderedOriginalPathnameListBuilder):
    """
    Represents classes that parse a music directory catalogue in order to
    build an updated version of an existing ratings file.
    """

    def __init__(self, w, currRatingsFile, defaultRating, ratingsMap = None):
        """
        Initializes us with the file/stream object to use to write out the
        updated ratings file, the pathname of the ratings file that is to
        be updated, and the rating to be given to new music files that are
        added to the ratings file.

        If 'ratingsMap' is not None then for each file its original file's
        pathname is searched for in 'ratingsMap' and if it is mapped to a
        rating then that rating is used in place of 'defaultRating' for that
        file.
        """
        #debug("---> in fs_UpdatedRatingsFileBuilder.__init__(w, %s, %i, %s)" % (currRatingsFile, defaultRating, ut.ut_prettyShortMap(ratingsMap)))
        assert w is not None
        assert currRatingsFile is not None
        assert os.path.isfile(currRatingsFile)
        assert defaultRating >= 0
        # 'ratingsMap' may be None
        fs_OrderedOriginalPathnameListBuilder. \
            __init__(self, w, _conf.baseSubdir)
        self._fs_currRatingsFile = currRatingsFile
        self._fs_currRatingsFileReader = None
        self._fs_currRatingsFileLine = None
        self._fs_defaultRating = defaultRating
        self._fs_ratingsMap = ratingsMap

    def _fs_beforeParsing(self):
        fs_OrderedOriginalPathnameListBuilder._fs_beforeParsing(self)
        self._fs_currRatingsFileReader = open(self._fs_currRatingsFile, 'r')

    def _fs_writeLinesFor(self, path, info):
        #debug("---> in _fs_writeLinesFor(%s, info)" % path)
        assert path is not None
        assert info is not None
        r = self._fs_currRatingsFileReader
        doWritePathLine = True
        doneUpToPath = False
        m = self._fs_ratingsMap
        while not doneUpToPath:
            currLine = self._fs_currRatingsFileLine
            #debug("    currLine = [%s]" % currLine)
            if currLine is not None:
                self._fs_currRatingsFileLine = None
            else:
                currLine = r.readline()
                #debug("    currLine = [%s] (from reader)" % currLine)
            if not currLine:
                #debug("    at end of current ratings file")
                doneUpToPath = True
            else:
                (currRating, currPath) = fs_parseRatingsFileLine(currLine)
                #debug("    curr rating = '%s', curr path = [%s]" % (currRating, currPath))
                if currPath is None:
                    self._fs_reportError("Found (and are discarding) an "
                        "invalid line in the ratings file '%s' when trying "
                        "to update it: the line is [%s]" %
                        (self._fs_currRatingsFile, line))
                elif currRating is None:
                    #debug("    curr line is a comment line")
                    self._fs_write(currLine)
                else:
                    #debug("    compare path [%s] and currPath [%s] ..." % (path, currPath))
                    cr = _fs_catalogueCompareFilePathnames(path, currPath)
                    #debug("        result = %i" % cr)
                    if cr < 0:
                        # A line for 'path' would come before 'currLine', so
                        # output a line for 'path' and save 'currLine' to
                        # compare to the next catalogue file element.
                        self._fs_currRatingsFileLine = currLine
                        doWritePathLine = True
                        doneUpToPath = True
                    elif cr > 0:
                        # 'currLine' precedes a line for 'path', so output
                        # 'currLine' and check for other lines in the current
                        # ratings file that might precede (or match) 'path'.
                        if m is not None:
                            #debug("    using ratings map in updating ratings file/1")
                            #debug("    using orig. path [%s] as key" % path)
                            nr = _fs_findNewRating(m, path)  # new rating
                            #debug("    new rating = %s" % str(nr))
                            if nr is not None:
                                currLine = _fs_buildRatingsFileLine(nr,
                                                currPath, addNewline = True)
                            #debug("    currLine = [%s]" % currLine)
                        self._fs_write(currLine)
                        doneUpToPath = False
                    else:
                        # Output 'currLine' in place of a new line for 'path'
                        assert cr == 0
                        doWritePathLine = False
                        doneUpToPath = True
                        if m is not None:
                            #debug("    using ratings map in updating ratings file/2")
                            #debug("    using orig. path [%s] as key" % path)
                            nr = _fs_findNewRating(m, path)  # new rating
                            #debug("    new rating = %s" % str(nr))
                            if nr is not None:
                                currLine = _fs_buildRatingsFileLine(nr,
                                                currPath, addNewline = True)
                            #debug("    currLine = [%s]" % currLine)
                        self._fs_write(currLine)
        if doWritePathLine:
            # Note: the line for 'path' isn't in the ratings file, so it is
            # assumed not to be in 'm' either: we use the default rating.
            #debug("    are writing line for path [%s]" % path)
            self._fs_writeLine(_fs_buildRatingsFileLine(self.
                                        _fs_defaultRating, path))

    def _fs_afterParsing(self):
        """
        Performs and processing that there is to do after we have finished
        parsing the entire catalogue.
        """
        #debug("---> in fs_UpdatedRatingsFileBuilder._fs_afterParsing()")
        m = self._fs_ratingsMap
        try:
            r = self._fs_currRatingsFileReader
            if r is not None:
                # Write out any lines left in the current ratings file.
                while True:
                    line = r.readline()
                    if not line:
                        break  # while
                    elif m is not None:
                        #debug("    using ratings map in updating ratings file/3")
                        (rating, path) = fs_parseRatingsFileLine(line)
                        if path is None:
                            self._fs_reportError("Found (and are discarding)"
                                " an invalid line in the ratings file '%s' "
                                "when trying to update it: the line is "
                                "[%s]" % (self._fs_currRatingsFile, line))
                        elif rating is not None:  # 'line' isn't a comment
                            #debug("    using orig. path [%s] as key" % path)
                            nr = _fs_findNewRating(m, path)
                            #debug("    new rating = %s" % str(nr))
                            if nr is not None:
                                line = _fs_buildRatingsFileLine(nr, path,
                                                        addNewline = True)
                            #debug("    line = [%s]" % line)
                    self._fs_write(line)
                ut.ut_tryToCloseAll(r)
                self._fs_currRatingsFileReader = None
        finally:
            fs_OrderedOriginalPathnameListBuilder._fs_afterParsing(self)

class fs_ChangeRatingsCommandProcessor(ut.ut_AbstractCommandFifoDaemonProcess):
    """
    Represents a daemon process that reads commands to change music file
    ratings from a FIFO and processes them.

    Each command consists of a single line, and must be terminated with a
    newline. The valid commands, where 'base' is the root or base name of
    the ratings file in which a rating is to be changed or information is to
    be updated and 'pathname' is the pathname - relative to the root (NOT
    base) music directory - of the music file whose rating is to be changed,
    are:

        =n base pathname

            Sets the music file's rating in the ratings file to 'n' or
            to config.maxRating if n > config.maxRating, where n >= 0.

        +n base pathname

            Increases the music file's rating by 'n' up to a maximum value
            of config.maxRating, where n >= 0.

        -n base pathname

            Decreases the music file's rating by 'n' down to a minimum of 1,
            where n >= 0. (A file's rating cannot be decreased to 0: it can
            only be explicitly set to 0.)

        refresh base [internal | external]

            Refreshes/updates the files and information related to the
            ratings corresponding to 'base'. If the command ends with
            'internal' then the ratings-related files (such as ratings files
            and database/DBM files) are updated so that they are in sync with
            each other, but if the command ends with 'external' then the
            ratings-related files are also updated with the information from
            the current main music directory catalogue.

    Note: the POSIX standard only guarantees that data is atomically written
    to a FIFO if that data is 512 bytes long or less, so we keep the commands
    as short as possible.
    """

    def __init__(self, commandSource, pidFile = None, doDebug = False):
        """
        Initializes us with the pathname of the FIFO from which we are to
        read commands to change ratings, and the pathname of the file to
        which we are to write our PID.
        """
        #self._ut_debug("---> in fs_ChangeRatingsCommandProcessor.__init__(%s, %s)" % (commandSource, pidFile))
        assert commandSource is not None
        # 'pidFile' may be None
        ut.ut_AbstractCommandFifoDaemonProcess. \
            __init__(self, commandSource, pidFile, doDebug)

    def _ut_reportError(self, msg):
        """
        Reports the error described by the message 'msg'.
        """
        report(_fs_daemonMessageFormat % msg)

    def _ut_debug(self, msg):
        """
        Reports 'msg' as a debugging message, if we're reporting them.
        """
        debug(_fs_daemonMessageFormat % msg)


    def _ut_beforeRunning(self):
        #self._ut_debug("---> in fs_ChangeRatingsCommandProcessor._ut_beforeRunning()")
        # Make sure all of our files are in sync, THEN process commands.
        for base in _conf.allRatingsBasenames:
            self._fs_internalRefresh(base)

    def _ut_processCommand(self, cmd):
        """
        Processes the ratings change command 'cmd'.

        See our class' comment for the syntax of all of the valid commands.
        """
        #self._ut_debug("---> in fs_ChangeRatingsCommandProcessor._ut_processCommand('%s')" % cmd)
        parts = cmd.split(None, 1)
        numParts = len(parts)
        assert numParts <= 2
        if numParts == 2:
            (cmdStart, rest) = parts
        elif numParts == 1:
            cmdStart = parts[0]
            rest = ""
        if numParts > 0:  # ignore empty/blank lines/commands
            assert cmdStart
            if cmdStart == _fs_refreshRatingsCommand:
                self._fs_processRefreshCommand(cmdStart, rest, cmd)
            elif cmdStart[0] in "+-=":
                self._fs_processChangeRatingCommand(cmdStart, rest, cmd)
            else:
                self._ut_reportInvalidCommandStartError(cmd)

    def _fs_processRefreshCommand(self, cmdStart, args, cmd):
        """
        Processes the "refresh ..." command whose first word is 'cmdStart'
        and the rest of which is in the string 'args'.

        'cmd' is the command that 'cmdStart' and 'args' are parts of: 'cmd'
        is only used in error messages.
        """
        #self._ut_debug("---> in _fs_processRefreshCommand(%s, %s, %s)" % (cmdStart, args, cmd))
        assert cmdStart == _fs_refreshRatingsCommand
        assert args is not None  # though it may be empty
        assert cmd
        parts = args.split()
        numParts = len(parts)
        #self._ut_debug("    parts = %s, numParts = %i" % (str(parts), numParts))
        types = _fs_allRatingsRefreshTypes
        if numParts == 2:
            #self._ut_debug("    are 2 args: base = '%s', type = '%s'" % tuple(parts))
            (base, type) = parts
            if self._fs_checkKnownRatingsBasename(base, cmd):
                #self._ut_debug("    '%s' is a known ratings file base name" % base)
                if type in types:
                    if type == _fs_internalRefreshType:
                        self._fs_internalRefresh(base)
                    else:
                        assert type == _fs_externalRefreshType
                        self._fs_externalRefresh(base)
                else:
                    t = ", ".join(['"%s"' % s for s in types])
                    self._ut_reportError("The command '%s' is invalid: "
                        "the last argument '%s' isn't a valid refresh "
                        "type (one of %s)." % (cmd, type, t))
            else:
                self._ut_reportError("The command '%s' is invalid: '%s' "
                    "is an unknown ratings file base name." % (cmd, base))
        elif numParts > 2:
            self._ut_reportTooManyCommandArguments(cmd)
        elif numParts == 1:
            t = ", ".join(['"%s"' % s for s in types])
            self._ut_reportError("The command '%s' is invalid: the "
                "refresh type (one of %s) argument is missing." % (cmd, t))
        else:
            assert numParts == 0

    def _fs_processChangeRatingCommand(self, cmdStart, args, cmd):
        """
        Processes the command that changes a music file's rating whose first
        word is 'cmdStart' and the rest of which is in the string 'args'.

        'cmd' is the command that 'cmdStart' and 'args' are parts of: 'cmd'
        is only used in error messages.
        """
        #self._ut_debug("---> _fs_processChangeRatingCommand(%s, %s, %s)" % (cmdStart, repr(args), cmd))
        assert cmdStart
        assert args is not None  # though it may be empty
        assert cmd
        result = False
        (op, amount) = self._fs_parseChangeRatingCommandStart(cmdStart, cmd)
        #self._ut_debug("    op = [%s], amount = [%s]" % (op, amount))
        if op is not None:
            (base, pathname) = self. \
                _fs_parseRatingsBasenameAndPathnameArguments(args, cmd)
            #self._ut_debug("    base = [%s], pathname = [%s]" % (base, pathname))
            if base is not None:
                adj = self._fs_buildRatingAdjuster(cmdStart, cmd)
                if adj is not None:
                    result = self._fs_adjustRatingFor(pathname, base, adj)
        return result

    def _fs_parseChangeRatingCommandStart(self, cmdStart, cmd):
        """
        Parses the first word 'cmdStart' of a command that changes a music
        file's rating into its operator part and its (integer) amount part:
        if it's successful then they're returned as a pair (with the operator
        first); otherwise one or more errors are reported and (None, None) is
        returned.

        'cmd' is the command that 'args' is a substring of: 'cmd' is only
        used in error messages.
        """
        assert cmdStart
        assert cmd
        result = (None, None)
        (op, strAmount) = (cmdStart[0], cmdStart[1:])
        if strAmount:
            try:
                amount = int(strAmount)
                if amount < 0:
                    self._ut_reportError("The command '%s' is invalid: the "
                        "amount '%i' in its first word '%s' is negative." %
                        (cmd, amount, cmdStart))
                else:
                    result = (op, amount)
            except:
                self._ut_reportError("The command '%s' is invalid: the "
                    "amount '%s' in its first word '%s' is not an integer." %
                    (cmd, strAmount, cmdStart))
        else:
            self._ut_reportError("The command '%s' is invalid: the first "
                "word '%s' must include an amount." % (cmd, cmdStart))
        assert len(result) == 2
        assert (result[0] is None) == (result[1] is None)
        assert result[0] is None or result[0]
        assert result[1] is None or result[1] >= 0
        return result

    def _fs_parseRatingsBasenameAndPathnameArguments(self, args, cmd):
        """
        Parses the command arguments string 'args' into a ratings file base
        name and a music file pathname: if they're successfully parsed and
        the ratings base name is a known ratings file base name then they're
        returned as a pair (with the ratings file base name first); otherwise
        one or more errors are reported and (None, None) is returned.

        'cmd' is the command that 'args' is a substring of: 'cmd' is only
        used in error messages.
        """
        assert args is not None
        assert cmd
        result = (None, None)
        parts = args.split(None, 1)
        numParts = len(parts)
        assert numParts <= 2
        if numParts == 0:
            self._ut_reportError("The command '%s' is invalid: no ratings "
                "file base name or music file pathname was specified." % cmd)
        elif numParts == 1:
            self._ut_reportError("The command '%s' is invalid: no music "
                "file pathname was specified." % cmd)
        elif self._fs_checkKnownRatingsBasename(parts[0], cmd):
            result = tuple(parts)
        assert len(result) == 2
        assert (result[0] is None) == (result[1] is None)
        assert result[0] is None or result[0]
        assert result[1] is None or result[1]
        return result

    def _fs_checkKnownRatingsBasename(self, base, cmd):
        """
        Checks whether 'base' is the base name of a known ratings file,
        returning True if it is, and reporting an error and returning False
        if it isn't.

        'cmd' is the command that 'base' is a substring of: 'cmd' is only
        used in error messages.
        """
        assert base
        assert cmd
        result = True
        if base not in _conf.allRatingsBasenames:
            result = False
            self._ut_reportError("The command '%s' is invalid: '%s' is not "
                "the base name of a known ratings file." % (cmd, base))
        return result


    def _fs_adjustRatingFor(self, path, base, adjuster):
        """
        Adjusts the ratings from the ratings file with basename 'base' for
        the music file with pathname 'path' to the result of passing the
        current rating to the 'adjuster' function.

        Returns True if the file's rating is successfully adjusted; otherwise
        one or more errors are reported as False is returned.
        """
        #self._ut_debug("---> in _fs_adjustRatingFor(%s, %s, adjuster)" % (path, base))
        assert path is not None
        assert base is not None
        #assert base in _conf.allRatingsBasenames
        assert adjuster is not None
        result = False
        (p2o, o2r) = (None, None)
        try:
            f = _fs_pathnameToOriginalPathnameDbmFilename
            p2o = _fs_openMetadataDbmFile(f)
            o2r = _fs_openRatingsDbmFile(base, 'c')
            try:
                origPath = p2o[str(path)]
                #self._ut_debug("    original file's path = [%s]" % origPath)
                try:
                    oldRating = o2r[origPath]
                    # no prefix since all pathnames in p2o are relative
                    # to the base music dir
                    #self._ut_debug("    old rating = %s" % oldRating)
                    oldRating = int(oldRating)
                    newRating = adjuster(oldRating)
                    #self._ut_debug("    new rating = %i" % newRating)
                    if newRating != oldRating:
                        o2r[str(origPath)] = str(newRating)
                        #self._ut_debug("    rating successfully adjusted")
                        result = True
                    else:
                        #self._ut_debug("    done: new and old ratings are the same")
                        pass
                except KeyError:
                    self._ut_reportError("There is no rating for the "
                        "music file '%s' (with original pathname '%s'), so "
                        "we can't update it." % (path, origPath))
            except KeyError:
                self._ut_reportError("The file with pathname '%s' isn't a "
                    "music file that we know about." % path)
        finally:
            ut.ut_tryToCloseAll(o2r, p2o)
        #self._ut_debug("    result = %s" % str(result))
        return result

    def _fs_buildRatingAdjuster(self, cmdStart, cmd):
        """
        Given the first "word" 'cmdStart' of the rating change command 'cmd',
        if 'cmdStart' is valid then we return a one-argument function that,
        given a rating, returns the result of adjusting the rating according
        to the command. If 'cmdStart' is invalid then we report one or more
        errors describing why and return None.

        Note: 'cmd' is only used in error messages.
        """
        #self._ut_debug("---> in _fs_buildRatingAdjuster(%s, %s)" % (cmdStart, cmd))
        assert cmdStart is not None
        assert cmd is not None
        result = None
        (op, strAmount) = (cmdStart[0], cmdStart[1:])
        try:
            amount = ut.ut_parseInt(strAmount, minValue = 0)
        except:
            self._ut_reportError("The command '%s' is invalid because the "
                "value '%s' after the operator '%s' isn't a non-negative "
                "integer." % (cmd, strAmount, op))
        else:
            assert amount >= 0
            if op == '-':
                # Don't let the rating be decreased below 1, but leave it
                # at 0 if it was already 0.
                result = lambda r, n = amount: min(max(1, r - n), r)
            elif op == '+':
                # Don't let the rating be increased above 'maxRating'.
                result = lambda r, n = amount: min(config.maxRating, r + n)
            elif op == '=':
                # Don't let the rating be set below 0 (since amount >= 0) or
                # above 'maxRating'.
                result = lambda r, n = amount: min(config.maxRating, n)
            else:
                self._ut_reportError("The command '%s' is invalid because "
                    "a valid command cannot start with the operator '%s'." %
                    (cmd, op))
        # 'result' may be None
        return result

    def _fs_internalRefresh(self, base):
        """
        Refreshes files and other information related to the ratings file
        with base name 'base' so that they're all in sync.

        Note: a given file is either successfully refreshed or left
        unchanged: a file will not be partially refreshed.

        Returns True if refreshing the files is successful; otherwise one or
        more errors are reported and False is returned.
        """
        #self._ut_debug("---> in _fs_internalRefresh(%s)" % base)
        assert base
        result = False
        rpath = fs_ratingsFilePathname(base)
        dpath = _fs_originalPathnameToRatingDbmFilePathname(base)
        isRatingsFile = os.path.exists(rpath)
        isDbFile = os.path.exists(dpath)
        if isRatingsFile and isDbFile:
            #self._ut_debug("    both ratings and db files exist")
            # Update the ratings in the ratings file from the database iff
            # the ratings file is not strictly newer than the database file.
            if ut.ut_doUpdateFile(rpath, dpath):
                result = self._fs_updateRatingsFileRatingsFromDatabase(base,
                                                                rpath, dpath)
            else:
                result = True  # there's nothing to do
        elif isRatingsFile:
            #self._ut_debug("    ratings file exists, db file doesn't")
            # Create the database file from the ratings file.
            result = self. \
                _fs_refreshOriginalPathnameToRatingDatabaseFile(base)
        else:
            #self._ut_debug("    ratings file doesn't exist ...")
            # Create the ratings file from the main catalogue file.
            cp = _conf.cataloguePathname
            result = self._fs_checkCatalogueExistsForRefresh(base, cp) and \
                self._fs_createRatingsFile(rpath, cp)
            if result:
                if isDbFile:
                    #self._ut_debug("    ... but the db file does exist")
                    # Update the ratings file's ratings from the db file.
                    self._fs_updateRatingsFileRatingsFromDatabase(base,
                                                              rpath, dpath)
                else:
                    #self._ut_debug("    ... and neither does the db file")
                    # Create the database file from the new ratings file.
                    self._fs_refreshOriginalPathnameToRatingDatabaseFile(base)
        #self._ut_debug("    result = %s" % str(result))
        return result

    def _fs_externalRefresh(self, base):
        """
        Refreshes files and other information related to the ratings file
        with base name 'base' so that they're all in sync, and so that they
        contain the information from the current version of the main music
        directory catalogue.

        Note: a given file is either successfully refreshed or left
        unchanged: a file will not be partially refreshed.

        Returns True if refreshing the files is successful; otherwise one or
        more errors are reported and False is returned.
        """
        #self._ut_debug("---> in _fs_externalRefresh(%s)" % base)
        assert base
        result = self._fs_checkCatalogueExistsForRefresh(base)
        if result:
            rpath = fs_ratingsFilePathname(base)
            dpath = _fs_originalPathnameToRatingDbmFilePathname(base)
            isDbFile = os.path.exists(dpath)
            if isDbFile:
                #self._ut_debug("    db file exists: use in refreshing ratings file")
                dp = dpath
            else:
                #self._ut_debug("    db file doesn't exist")
                dp = None
            result = self._fs_refreshRatingsFileFromCatalogue(rpath, dp)
            if result:
                #self._ut_debug("    (re)build db file from ratings file")
                ut.ut_tryToDeleteAll(dpath)
                    # We delete and rebuild the db so that it contains any
                    # new entries from the catalogue.
                result = self. \
                    _fs_refreshOriginalPathnameToRatingDatabaseFile(base)
        #self._ut_debug("    result = %s" % str(result))
        return result

    def _fs_checkCatalogueExistsForRefresh(self, base, catPath = None):
        """
        Checks that the main music directory catalogue file with pathname
        'catPath' (or the one from the configuration if 'catPath' is None)
        exists and is a regular file, for the purposes of refreshing the
        ratings information corresponding to the ratings file with base
        name 'base'.

        Returns True if it is, and reports an error and returns False if it
        isn't.
        """
        assert base
        # 'catPath' may be None
        if catPath is None:
            catPath = _conf.cataloguePathname
        result = os.path.isfile(catPath)
        if not result:
           self._ut_reportError("Refreshing the '%s' ratings information "
            "failed: the main music directory catalogue file '%s' either "
            "doesn't exist or isn't a regular file." % (base, catPath))
        return result

    def _fs_updateRatingsFileRatingsFromDatabase(self, base,
                                                 ratingsPath, dbPath):
        """
        Updates the ratings in the ratings file with base name 'base' and
        pathname 'ratingsPath' so that its rating for each file is the one
        obtained from the DBM file with pathname 'dbPath' if it has a mapping
        for it: otherwise the rating will be the one already in the ratings
        file.

        Returns True if the ratings file is successfully updated, and reports
        one or more errors and returns False otherwise.
        """
        #self._ut_debug("---> in _fs_updateRatingsFileRatingsFromDatabase(%s, %s, %s)" % (base, ratingsPath, dbPath))
        assert base
        assert ratingsPath is not None
        assert dbPath is not None
        result = False
        r = None
        m = None
        (w, tmpPath) = (None, None)
        (d, f) = os.path.split(ratingsPath)
        try:
            r = open(ratingsPath, 'r')
            m = _fs_openDbmFile(dbPath)
            (w, tmpPath) = ut.ut_createTemporaryFile(d, f + "-")
            #self._ut_debug("    created temp. ratings file [%s]" % tmpPath)
            result = True
            lineNum = 0
            for line in r:
                lineNum += 1
                (oldRating, path) = fs_parseRatingsFileLine(line)
                if oldRating is not None:
                    newRating = _fs_findNewRating(m, path, oldRating)
                    w.write(_fs_buildRatingsFileLine(newRating, path,
                                                     addNewline = True))
                elif path is None:
                    self._ut_reportError("Updating ratings in the '%s' "
                        "ratings file from the database failed: line #%i "
                        "in the ratings file is invalid." % (base, lineNum,
                        ratingsPath))
                    result = False
                    break
            if result:
                #self._ut_debug("    refresh worked: renaming temp file '%s' to real file '%s'" % (tmpPath, ratingsPath))
                try:
                    w.close()
                    w = None
                    os.rename(tmpPath, ratingsPath)
                except:
                    result = False
        finally:
            ut.ut_tryToCloseAll(r, m, w)
            ut.ut_deleteFileOrDirectory(tmpPath)
        #self._ut_debug("    result = %s" % str(result))
        return result


    def _fs_refreshRatingsFileFromCatalogue(self, path,
                                            ratingsDbPath = None):
        """
        Ensures that the ratings file with pathname 'path' exists and
        contains ratings for all of the original files in the main music
        directory catalogue.

        If 'ratingsDbPath' is not None then it is assumed to be the pathname
        of a DBM file that maps original file pathnames to their ratings: for
        each file its original file's pathname is searched for in the DBM
        file/map and if it is mapped to a rating then that rating is used in
        the ratings file in place of the rating already in the ratings file
        for that file. (The DBM file is also considered to be a dependency in
        determining whether the ratings file needs to be updated.

        Returns True iff the ratings file is successfully refreshed.
        """
        #self._ut_debug("---> in _fs_refreshRatingsFileFromCatalogue(%s, %s)" % (path, ratingsDbPath))
        assert path is not None
        # 'ratingsDbPath' may be None
        result = True
        m = None
        try:
            if ratingsDbPath is not None:
                m = _fs_openDbmFile(ratingsDbPath)
            catPath = _conf.cataloguePathname
            if os.path.isfile(path):
                if ut.ut_doUpdateFile(path, catPath, ratingsDbPath):
                    result = self._fs_updateRatingsFile(path, catPath, m)
                else:
                    #self._ut_debug("ratings file '%s' is already up to date" % path)
                    result = True
            elif not os.path.lexists(path):
                result = self._fs_createRatingsFile(path, catPath, m)
            else:
                self._ut_reportError("Refreshing the ratings file '%s' "
                    "failed: it already exists but isn't a regular file." %
                    path)
                result = False
        finally:
            ut.ut_tryToCloseAll(m)
        #self._ut_debug("    result = %s" % str(result))
        return result

    def _fs_updateRatingsFile(self, path, catPath, ratingsMap = None):
        """
        Updates an existing ratings file with pathname 'path' by adding
        entries to it for new files in the music directory catalogue file
        with pathname 'catPath'.

        If 'ratingsMap' is not None then for each file its original file's
        pathname is searched for in 'ratingsMap' and if it is mapped to a
        rating then that rating is used in the ratings file in place of the
        rating already in the ratings file for that file. (Entries from the
        catalogue for new files are assumed not to be in 'ratingsMap' (since
        they're not in the ratings file) so the default rating is always used
        for those files.)

        Returns True iff the ratings file is successfully updated.
        """
        #self._ut_debug("---> in _fs_updateRatingsFile(%s, %s, %s)" % (path, catPath, ut.ut_prettyShortMap(ratingsMap)))
        assert path is not None
        assert os.path.isfile(path)
        assert catPath is not None
        # 'ratingsMap' may be None
        defaultRating = int(_conf.defaultRating)
        bc = lambda w, p = path, dr = defaultRating, m = ratingsMap: \
                fs_UpdatedRatingsFileBuilder(w, p, dr, m)
        result = self._fs_createOrUpdateRatingsFile(path, catPath, bc)
        #self._ut_debug("    result = %s" % str(result))
        return result

    def _fs_createRatingsFile(self, path, catPath, ratingsMap = None):
        """
        Creates the ratings file with pathname 'path' from the contents of
        the music directory catalogue file with pathname 'catPath',
        replacing any existing file.

        If 'ratingsMap' is not None then for each file its original file's
        pathname is searched for in 'ratingsMap' and if it is mapped to a
        rating then that rating is used in the ratings file in place of the
        default rating for that file.

        Returns True iff the ratings file is successfully created.
        """
        #self._ut_debug("---> in _fs_createRatingsFile(%s, %s, %s)" % (path, catPath, ut.ut_prettyShortMap(ratingsMap)))
        assert path is not None
        assert catPath is not None
        # 'ratingsMap' may be None
        defaultRating = int(_conf.defaultRating)
        bc = lambda w, dr = defaultRating, m = ratingsMap: \
                fs_NewRatingsFileBuilder(w, dr, m)
        result = self._fs_createOrUpdateRatingsFile(path, catPath, bc)
        #self._ut_debug("    result = %s" % str(result))
        return result

    def _fs_createOrUpdateRatingsFile(self, path, catPath, builderCtor):
        """
        Creates or updates - depending on the builder that 'builderCtor'
        constructs when it is called - a ratings file with pathname 'path'
        using information from the music directory catalogue file with
        pathname 'catPath'.

        'builderCtor' is assumed to be a 1-argument function whose argument
        is the file/stream object to which the new/updated contents of the
        ratings file are to be written to (initially)

        See _fs_createRatingsFile().
        See _fs_updateRatingsFile().

        Returns True iff the ratings file is successfully created or updated.
        """
        #self._ut_debug("---> in _fs_createOrUpdateRatingsFile(%s, %s, builderCtor)" % (path, catPath))
        assert path is not None
        assert catPath is not None
        assert builderCtor is not None
        result = False
        (d, f) = os.path.split(path)
        (w, tmpPath) = (None, None)
        try:
            (w, tmpPath) = ut.ut_createTemporaryFile(d, f + "-")
            #self._ut_debug("    created temp. ratings file [%s]" % tmpPath)
            b = builderCtor(w)
            #self._ut_debug("    built builder of type '%s'" % type(b))
            b.fs_parse(catPath)
            w.close()
            w = None
            os.rename(tmpPath, path)
            #self._ut_debug("    renamed temp. ratings file [%s] to real ratings file [%s]" % (tmpPath, path))
            result = True
        finally:
            ut.ut_tryToCloseAll(w)
            ut.ut_deleteFileOrDirectory(tmpPath)
        #self._ut_debug("    result = %s" % str(result))
        return result


    def _fs_refreshOriginalPathnameToRatingDatabaseFile(self, base):
        """
        Creates (if it doesn't exist) or updates (if it does exist) the
        DBM file that maps each original music file's pathname to its rating
        from the ratings file with basename 'base'.

        Returns True iff the database file is successfully refreshed.
        """
        #self._ut_debug("---> in _fs_refreshOriginalPathnameToRatingDatabaseFile(%s)" % base)
        assert base is not None
        result = False
        m = None
        r = None
        try:
            m = _fs_openRatingsDbmFile(base, "n")
            r = open(fs_ratingsFilePathname(base), 'r')
            lineNum = 0
            baseSubdir = _conf.baseSubdir
            result = True
            for line in r:
                lineNum += 1
                (rating, path) = fs_parseRatingsFileLine(line)
                if rating is not None:
                    assert path is not None
                    key = os.path.join(baseSubdir, path)
                        # since the main catalogue's pathnames are relative
                        # to the rootDir and the ones in ratings files are
                        # relative to the baseDir
                    m[str(key)] = str(rating)
                        # we apply str() to the key since DBM files don't
                        # deal well with Unicode strings.
                elif path is None:
                    self._ut_reportError("line #%i in the ratings file with "
                        "basename '%s' is invalid" % (lineNum, base))
                    result = False
        finally:
            ut.ut_tryToCloseAll(m, r)
        return result


class fs_PlaylistSelectionCriteria(object):
    """
    Represents classes that contain the criteria that are used to determine
    whether music files can be in a given playlist.

    Note: exclusions override inclusions, so if, for example, a format is
    both included and excluded then it will be excluded. If nothing is
    either included or excluded for a given aspect (such as genre, for
    example) then that aspect will not limit which music files can be in a
    playlist.
    """

    def __init__(self):
        object.__init__(self)
        self._fs_mustBeOriginal = True
        self._fs_includedKinds = set()
        self._fs_excludedKinds = set()
        self._fs_includedFormats = set()
        self._fs_excludedFormats = set()
        self._fs_includedGenres = set()
        self._fs_excludedGenres = set()

    def fs_canBeIncluded(self, info):
        """
        Returns True iff the music file described by 'info (a
        fs_CataloguedFileInformation object) is eligible for inclusion in a
        playlist.
        """
        result = True
        if self._fs_mustBeOriginal:
            result = info.fs_isOriginalFile()
        (inc, exc) = (self._fs_includedKinds, self._fs_excludedKinds)
        if result and not self._fs_areBothEmpty(inc, exc):
            val = fs_fileKindFromInformation(info)
            result = self._fs_canInclude(val, inc, exc)
        (inc, exc) = (self._fs_includedFormats, self._fs_excludedFormats)
        if result and not self._fs_areBothEmpty(inc, exc):
            val = fs_fileFormatFromInformation(info)
            result = self._fs_canInclude(val, inc, exc)
        (inc, exc) = (self._fs_includedGenres, self._fs_excludedGenres)
        if result and not self._fs_areBothEmpty(inc, exc):
            val = fs_fileGenreFromInformation(info)
            result = self._fs_canInclude(val, inc, exc)
        return result

    def _fs_canInclude(self, value, inc, exc):
        """
        Returns True iff a file can be included in a playlist if 'value'
        isn't None and is found in the collection 'inc' (if 'inc' isn't
        empty) and is NOT found in the collection 'exc' (if 'exc' isn't
        empty).
        """
        return (value is not None) and \
            (not inc or value in inc) and (not exc or value not in exc)

    def fs_setMustBeOriginal(self, mustBe):
        """
        Sets whether a music file must be original in order to be eligible
        for inclusion in a playlist.

        By default a music file must be originals in order to be eligible.
        """
        self._fs_mustBeOriginal = mustBe

    def fs_includeKind(self, kind):
        """
        Adds 'kind' to the list of the kinds of music files that are eligible
        for inclusion in a playlist (unless the kind has also been excluded).

        See the configuration file for the valid music file kind values.
        """
        assert kind is not None
        self._fs_includedKinds.add(kind)

    def fs_excludeKind(self, kind):
        """
        Adds 'kind' to the list of the kinds of music files that are NOT
        eligible for inclusion in a playlist.

        See the configuration file for the valid music file kind values.
        """
        assert kind is not None
        self._fs_excludedKinds.add(kind)

    def fs_includeFormat(self, fmt):
        """
        Adds 'fmt' to the list of the formats of music files that are
        eligible for inclusion in a playlist (unless the format has also been
        excluded).

        See the configuration file for the valid music file format values.
        """
        assert fmt is not None
        self._fs_includedFormats.add(fmt)

    def fs_excludeFormat(self, fmt):
        """
        Adds 'fmt' to the list of the formats of music files that are NOT
        eligible for inclusion in a playlist.

        See the configuration file for the valid music file format values.
        """
        assert fmt is not None
        self._fs_excludedFormats.add(fmt)

    def fs_includeGenre(self, genre):
        """
        Adds 'genre' to the list of the genres of music that are eligible for
        inclusion in the playlist (unless the genre has also been excluded).
        """
        assert genre is not None
        self._fs_includedGenres.add(genre)

    def fs_excludeGenre(self, genre):
        """
        Adds 'genre' to the list of the genres of music that are NOT eligible
        for inclusion in the playlist.
        """
        assert genre is not None
        self._fs_excludedGenres.add(genre)


    def _fs_areBothEmpty(self, set1, set2):
        """
        Returns True iff both of the sets 'set1' and 'set2' are empty.
        """
        return len(set1) == 0 and len(set2) == 0

class fs_PlaylistCandidatePathnameListBuilder(fs_OrderedPathnameListBuilder):
    """
    Builds a list of music file pathnames from which to select ones to appear
    in a playlist.

    A pathname may appear in the list multiple times in a row in order to
    increase its chances of appearing in a playlist.
    """

    def __init__(self, w, criteria, ratingsMap, ratingsToChancesFunc):
        """
        Initializes us with the file/stream object to use to write out the
        playlist candidate pathname list, the fs_PlaylistSelectionCriteria
        to use to select which music files' pathnames are eligible to appear
        in the list, a map from the pathname of each original file to the
        rating for that file, and the one-argument function to use to convert
        a file's rating into the number of chances it has to appear in the
        list we generate.
        """
        #debug("---> in fs_PlaylistSelectionCriteria.__init__(w, criteria, %s, ratingsToChancesFunc)" % ut.ut_prettyShortMap(ratingsMap))
        assert w is not None
        assert criteria is not None
        assert ratingsMap is not None
        assert ratingsToChancesFunc is not None
        fs_OrderedPathnameListBuilder.__init__(self, w)
        self._fs_criteria = criteria
        self._fs_ratingsMap = ratingsMap
        self._fs_ratingToChancesFunc = ratingsToChancesFunc
        self._fs_lineCount = 0
        self._fs_candidateCount = 0

    def fs_lineCount(self):
        """
        Returns the number of lines we've written out so far.
        """
        result = self._fs_lineCount
        assert result >= 0
        return result

    def fs_candidateCount(self):
        """
        Returns the number of distinct music files whose pathnames have been
        written out at least once so far.
        """
        result = self._fs_candidateCount
        assert result >= 0
        return result


    def _fs_beforeParsing(self):
        fs_OrderedPathnameListBuilder._fs_beforeParsing(self)
        self._fs_lineCount = 0
        self._fs_candidateCount = 0

    def _fs_doIncludeFile(self, info):
        assert info is not None

        # The catalogue contains all of the files under the rootDir but
        # we only allow ones under the baseDir to be in playlists (though
        # we still want their pathnames to be relative to the rootDir).
        result = fs_OrderedPathnameListBuilder. \
            _fs_doIncludeFile(self, info) and \
            ut.ut_hasPathnamePrefix(info.fs_pathname(),
                                    _conf.baseSubdir) and \
            self._fs_criteria.fs_canBeIncluded(info)
        return result

    def _fs_writeLinesFor(self, path, info):
        #debug("---> in _fs_writeLinesFor(%s, info)" % path)
        assert path is not None
        assert info is not None
        origPath = self._fs_originalFilePathnameOrPathname(info)
        rating = int(self._fs_ratingsMap[str(origPath)])
        numChances = self._fs_ratingToChancesCount(rating)
        if numChances > 0:
            for i in xrange(numChances):
                self._fs_writeLine(path)
            self._fs_candidateCount += 1
            self._fs_lineCount += numChances

    def _fs_ratingToChancesCount(self, rating):
        """
        Returns the number of chances that a music file with rating 'rating'
        should have to appear in a playlist. It has no chance iff 'result' is
        zero.
        """
        assert rating >= 0
        result = self._fs_ratingToChancesFunc(rating)
        assert result >= 0
        return result


class fs_GeneratedPlaylistsBuilder(fs_AbstractMusicDirectoryCatalogueParser):
    """
    Parses a music directory catalogue into a directory tree of playlists
    that each contain an entry for each music file under a given subdirectory
    of the catalogue's music directory.

    Note: each playlist's entries will be in pathname order.
    """

    def __init__(self, playlistDir = None, subdir = ''):
        """
        Initializes us with the pathname of the directory under which we are
        to build/create the playlists (which will be None if the default
        generated playlists directory's pathname is to be used), and
        optionally the music directory subdirectory whose contents are the
        only music files we're to build playlists for.

        Note: regardless of the value of 'subdir' all of the pathnames that
        appear in playlist entries will be relative to the root (not the
        base) music directory.
        """
        # 'playlistDir' may be None
        assert subdir is not None
        fs_AbstractMusicDirectoryCatalogueParser.__init__(self)
        if playlistDir is None:
            playlistDir = _conf.generatedPlaylistsDir
        self._fs_playlistDir = playlistDir
        self._fs_subdir = subdir

    def _fs_processDirectoryStartInformation(self, info):
        #debug("---> in fs_GeneratedPlaylistsBuilder._fs_processDirectoryStartInformation(info)")
        assert info is not None
        p = info.fs_pathname()
        if self._fs_doProcess(p):
            #debug("    info.fs_pathname() = [%s]" % p)
            d = os.path.join(self._fs_playlistDir,
                             ut.ut_removePathnamePrefix(p, self._fs_subdir))
            #debug("    creating playlist dir [%s]" % d)
            ut.ut_createDirectory(d)
            for f in _fs_allGeneratedPlaylistFilenames:
                playlist = os.path.join(d, f)
                #debug("    deleting playlist [%s] iff it exists" % playlist)
                ut.ut_deleteFileOrDirectory(playlist)
        #debug("    done processing dir [%s]" % p)

    def _fs_processFileInformation(self, info):
        #debug("---> in fs_GeneratedPlaylistsBuilder._fs_processFileInformation(info)")
        assert info is not None
        p = info.fs_pathname()
        if self._fs_doProcess(p):
            #debug("    processing file [%s]" % p)
            pf = _fs_everythingPlaylistFilename
            self._fs_appendToAllPlaylists(p, pf)
            if info.fs_isOriginalFile():
                pf = _fs_originalsPlaylistFilename
                self._fs_appendToAllPlaylists(p, pf)
        #debug("    done processing file [%s]" % p)

    def _fs_appendToAllPlaylists(self, p, base):
        """
        Appends the pathname 'path' of an audio file to the end of the
        playlist files with basename 'base' in the playlist directory
        corresponding to the audio file's directory and all of its ancestor
        playlist directories.
        """
        #debug("---> in _fs_appendToAllPlaylists(%s, %s)" % (p, base))
        assert p is not None
        assert base is not None
        pdir = ut.ut_removeAnyPathnameSeparatorAtEnd(self._fs_playlistDir)
        d = os.path.join(pdir,
                         ut.ut_removePathnamePrefix(p, self._fs_subdir))
        while d != pdir:
            d = os.path.dirname(d)
            playlist = os.path.join(d, base)
            #debug("    appending to playlist [%s]" % playlist)
            ut.ut_appendFileLines(playlist, [p])
            #debug("    pdir = [%s], d = [%s]" % (pdir, d))
        #debug("    done appending path [%s] to all playlists" % p)

    def _fs_doProcess(self, path):
        """
        Returns True iff the file or directory with pathname 'path' (which is
        assumed to be relative to the root music directory) is to be
        processed as a part of building playlists.
        """
        #debug("---> in fs_GeneratedPlaylistsBuilder._fs_doProcess(%s)" % path)
        assert path is not None
        return ut.ut_hasPathnamePrefix(path, self._fs_subdir)


class fs_MusicMetadataManager(object):
    """
    Represents classes that manage all of the music metadata described by
    the configuration instance in the 'config' module.
    """

    def fs_title(self, path):
        """
        Returns the title of the audio file with pathname 'path', or None if
        'path' isn't the pathname of an audio file that we know about or its
        title is missing or can't be obtained.
        """
        assert path is not None
        result = self._fs_fileTagValue(path, music.mu_flacTrackTitleTag)
        # 'result' may be None
        return result

    def fs_trackNumber(self, path):
        """
        Returns the track number of the audio file with pathname 'path', or
        None if 'path' isn't the pathname of an audio file that we know about
        or its track number is missing or can't be obtained.

        Note: the result is a string (if it's not None).
        """
        assert path is not None
        result = self._fs_fileTagValue(path, music.mu_flacTrackNumberTag)
        # 'result' may be None
        return result

    def fs_albumTitle(self, path):
        """
        Returns the title of the audio file with pathname 'path', or None if
        'path' isn't the pathname of an audio file that we know about or its
        album title is missing or can't be obtained.

        Note: an audio file's title and album title will be the same if the
        audio file represents an album (and possibly in other cases too).
        """
        assert path is not None
        result = self._fs_fileTagValue(path, music.mu_flacAlbumTag)
        # 'result' may be None
        return result

    def fs_artist(self, path):
        """
        Returns the artist for the audio file with pathname 'path', or None
        if 'path' isn't the pathname of an audio file that we know about or
        its artist is missing or can't be obtained.
        """
        assert path is not None
        result = self._fs_fileTagValue(path, music.mu_flacArtistTag)
        # 'result' may be None
        return result

    def fs_genre(self, path):
        """
        Returns the genre for the audio file with pathname 'path', or None
        if 'path' isn't the pathname of an audio file that we know about or
        its genre is missing or can't be obtained.
        """
        assert path is not None
        result = self._fs_fileTagValue(path, music.mu_flacGenreTag)
        # 'result' may be None
        return result

    def fs_releaseDate(self, path):
        """
        Returns the release date for the audio file with pathname 'path', or
        None if 'path' isn't the pathname of an audio file that we know about
        or its release date is missing or can't be obtained.
        """
        assert path is not None
        result = self._fs_fileTagValue(path, music.mu_flacDateTag)
        # 'result' may be None
        return result

    def fs_comment(self, path):
        """
        Returns the comment associated with the audio file with pathname
        'path', or None if 'path' isn't the pathname of an audio file that we
        know about or its comment is missing or can't be obtained.
        """
        assert path is not None
        result = self._fs_fileTagValue(path, music.mu_flacCommentTag)
        # 'result' may be None
        return result


    def _fs_fileTagValue(self, path, name):
        """
        Returns the value of the tag named 'name' for the audio file with
        pathname 'path', or None if 'path' isn't the pathname of an audio
        file that we know about, or the audio file doesn't have a tag named
        'name'.
        """
        assert path is not None
        assert name is not None
        result = None
        info = self._fs_fileInformation(path)
        if info is not None:
            result = info.fs_tagValue(name)
        # 'result' may be None
        return result

    def _fs_fileInformation(self, path):
        """
        Returns a fs_CataloguedFileInformation object describing the audio
        file with pathname 'path' (relative to the root music directory), or
        returns None if 'path' isn't the pathname of an audio file that we
        know about or the file's information can't be obtained.
        """
        assert path is not None
        p2i = None
        try:
            f = _fs_pathnameToInfoShelfFilename
            p2i = _fs_openShelfFile(_fs_metadataDatabaseFilePathname(f))
            try:
                result = p2i[str(path)]
            except KeyError:
                result = None
        finally:
            ut.ut_tryToCloseAll(p2i)
        # 'result' may be None
        return result


    def fs_allRatings(self, paths, base = None, subdir = None):
        """
        Returns a list whose i'th item is:
            - the rating for the audio file whose pathname is the i'th item
              in 'paths' in the ratings file with base name 'base', or in
              the main ratings file if 'base' is None, or
            - None if the rating can't be obtained for the i'th item in
              'paths' (for example, if it isn't the pathname of a known
              audio file)

        Note: an audio file's rating can change at any time, so the result of
        this method may be incorrect by the time it's returned. Thus it
        should usually only be used for informational purposes (and not in
        calculations - like calculating a new rating - for example).

        If 'subdir' is None then each pathname in 'paths' will be assumed to
        be relative to the base music directory. But if 'subdir' isn't None
        then each pathname in 'paths' will be assumed to be relative to the
        subdirectory 'subdir' of the root (NOT the base) music directory.
        So if 'subdir' is the empty path '' then each pathname in 'paths'
        will be assumed to be relative to the root music directory.
        """
        assert paths is not None
        # 'base' may be None
        # 'subdir' may be None
        result = []
        join = os.path.join
        if base is None:
            base = _conf.mainRatingsBasename
        if subdir is None:
            subdir = _conf.baseSubdir
        p2o = None
        o2r = None
        try:
            f = _fs_pathnameToOriginalPathnameDbmFilename
            p2o = _fs_openMetadataDbmFile(f)
            o2r = _fs_openRatingsDbmFile(base)
            for path in paths:
                r = None
                p = join(subdir, path)
                #print "p = [%s]: subdir = [%s], path = [%s]" % (p, subdir, path)
                opath = None
                if p in p2o:
                    opath = p2o[p]
                if opath is not None:
                    r = None
                    if opath in o2r:
                        r = o2r[opath]
                    if r is not None:
                        r = int(r)
                result.append(r)
        finally:
            ut.ut_tryToCloseAll(o2r, p2o)
        assert result is not None
        assert len(result) == len(paths)
        #assert for r in result: r is None or r >= 0
        #assert for r in result: r is None or r <= config.maxRating
        return result

    def fs_rating(self, path, base = None, subdir = None):
        """
        Returns the rating for the audio file with pathname 'path' in the
        ratings file with base name 'base', or in the main ratings file if
        'base' is None, or returns None if the rating can't be obtained (for
        example, if 'path' isn't the pathname of a known audio file).

        Note: an audio file's rating can change at any time, so the result of
        this method may be incorrect by the time it's returned. Thus it
        should usually only be used for informational purposes (and not in
        calculations - like calculating a new rating - for example).

        If 'subdir' is None then 'path' will be assumed to be relative to the
        base music directory. But if 'subdir' isn't None then 'path' will be
        assumed to be relative to the subdirectory 'subdir' of the root (NOT
        the base) music directory. So if 'subdir' is the empty path '' then
        'path' will be assumed to be relative to the root music directory.
        """
        assert path is not None
        # 'base' may be None
        # 'subdir' may be None
        res = self.fs_allRatings([path], base, subdir)
        assert len(res) == 1
        result = res[0]
        assert result is None or result >= 0
        assert result is None or result <= config.maxRating
        return result

    def fs_increaseRating(self, amount, path, base = None, subdir = None):
        """
        Attempts to increase by 'amount' the rating for the audio file with
        pathname 'path' in the ratings file with base name 'base', or in the
        main ratings file if 'base' is None.

        Note: any attempt to increase the rating above the maximum rating
        will increase it to that maximum.

        See _fs_changeRating().
        """
        assert amount >= 0
        assert path is not None
        # 'base' may be None
        # 'subdir' may be None
        self._fs_changeRating("+", amount, path, base, subdir)

    def fs_decreaseRating(self, amount, path, base = None, subdir = None):
        """
        Attempts to decrease by 'amount' the rating for the audio file with
        pathname 'path' in the ratings file with base name 'base', or in the
        main ratings file if 'base' is None.

        Note: any attempt to decrease the rating below 1 will decrease it to
        1. (You can't decrease a rating to 0: you can only set it to 0.)

        See _fs_changeRating().
        """
        assert amount >= 0
        assert path is not None
        # 'base' may be None
        # 'subdir' may be None
        self._fs_changeRating("-", amount, path, base, subdir)

    def fs_setRating(self, amount, path, base = None, subdir = None):
        """
        Attempts to set to 'amount' the rating for the audio file with
        pathname 'path' in the ratings file with base name 'base', or in the
        main ratings file if 'base' is None.

        Note: any attempt to set the rating to one above the maximum rating
        will set it to that maximum.

        See _fs_changeRating().
        """
        assert amount >= 0
        assert path is not None
        # 'base' may be None
        # 'subdir' may be None
        self._fs_changeRating("=", amount, path, base, subdir)

    def _fs_changeRating(self, cmdOp, amount, path, base, subdir):
        """
        Attempts to change the rating for the audio file with pathname 'path'
        in the ratings file with base name 'base', or in the main ratings
        file if 'base' is None. How the rating in changed is determined by a
        combination of 'cmdOp' and 'amount'.

        If 'subdir' is None then 'path' will be assumed to be relative to the
        base music directory. But if 'subdir' isn't None then 'path' will be
        assumed to be relative to the subdirectory 'subdir' of the root (NOT
        the base) music directory. So if 'subdir' is the empty path '' then
        'path' will be assumed to be relative to the root music directory.
        """
        #debug("---> _fs_changeRating(%s, %s, %s, %s, %s)" % (cmdOp, amount, path, base, subdir))
        assert len(cmdOp) == 1
        assert cmdOp in "+-="
        assert amount >= 0
        assert path is not None
        # 'base' may be None
        # 'subdir' may be None
        if base is None:
            base = _conf.mainRatingsBasename
        if subdir is None:
            subdir = _conf.baseSubdir
        _fs_sendChangeRatingsCommand("%s%i %s %s" % (cmdOp, amount, base,
                                            os.path.join(subdir, path)))


    def fs_generatePlaylists(self, playlistDir = None, subdir = None):
        """
        Generates all of the playlists that can be generated automatically.

        See fs_GeneratedPlaylistsBuilder.
        """
        # 'playlistDir' may be None
        # 'subdir' may be None
        if subdir is None:
            subdir = _conf.baseSubdir
        b = fs_GeneratedPlaylistsBuilder(playlistDir, subdir)
        b.fs_parse(self._fs_cataloguePathname())

    def fs_createRandomPlaylist(self, w, criteria, size = None,
            base = None, ratingsToChancesMethod = None):
        """
        Writes out, using the file/stream object 'w', a "raw" playlist that
        contains the pathnames of music files randomly selected from those
        that satisfy the selection criteria specified by the
        fs_PlaylistSelectionCriteria 'criteria'.

        There will be 'size' pathnames in the playlist iff 'size' isn't None:
        if it is None then the playlist will contain the number of pathnames
        specified as a default in the configuration.
        """
        assert w is not None
        assert criteria is not None
        assert size is None or size > 0
        # 'base' may be None
        # 'ratingsToChancesMethod' may be None
        if size is None:
            size = _conf.defaultPlaylistSize
        if base is None:
            base = _conf.mainRatingsBasename
        if ratingsToChancesMethod is None:
            ratingsToChancesMethod = fs_defaultRatingToChancesConverter

        ratingsMap = None
        (tmpWriter, tmpPath) = (None, None)
        try:
            ratingsMap = _fs_openRatingsDbmFile(base)
            d = self._fs_playlistsDirectory()
            (tmpWriter, tmpPath) = ut.ut_createTemporaryFile(d,
                                        _fs_tempPlaylistCandidatesPrefix)
            b = fs_PlaylistCandidatePathnameListBuilder(tmpWriter, criteria,
                                        ratingsMap, ratingsToChancesMethod)
            b.fs_parse(self._fs_cataloguePathname())
            tmpWriter.close()
            tmpWriter = None
            fmt = "%s\n"
            for p in self._fs_randomPlaylistEntries(tmpPath, b, size):
                w.write(fmt % p)
        finally:
            ut.ut_tryToCloseAll(ratingsMap, tmpWriter)
            ut.ut_deleteFileOrDirectory(tmpPath)

    def _fs_randomPlaylistEntries(self, path, builder, size):
        """
        Returns the entries for a randomly-generated playlist from the
        pathnames in the playlist candidates file with pathname 'path' that
        was built by the fs_PlaylistCandidatePathnameListBuilder 'builder'.

        There will be 'size' entries unless there a fewer candidates than
        that, in which case entries for all of the candidates will be
        returned.
        """
        #debug("---> in _fs_randomPlaylistEntries(%s, builder, %s)" % (path, str(size)))
        assert path is not None
        assert builder is not None
        assert size >= 0
        if builder.fs_candidateCount() <= size:
            #debug("    returning all of the candidates' pathnames")
            s = set()
            r = None
            try:
                r = open(path, 'r')
                for line in r:
                    s.add(line.strip())
            finally:
                ut.ut_tryToCloseAll(r)
            result = list(s)
            random.shuffle(result)
        else:
            #debug("    selecting entries from the candidates ...")
            result = self. \
                _fs_selectRandomPlaylistEntries(path, builder, size)
            #debug("    ... finished selecting")
        assert result is not None
        return result

    def _fs_selectRandomPlaylistEntries(self, path, builder, size,
                                        selectionSize = None):
        """
        Returns the entries selected for a randomly-generated playlist from
        the pathnames in the playlist candidates file with pathname 'path'
        that was built by the fs_PlaylistCandidatePathnameListBuilder
        'builder'.

        There will be 'size' entries unless there a fewer candidates than
        that, in which case entries for all of the candidates will be
        returned.

        Note: 'selectionSize' should always be left as the default in user
        code. Non-default values are only intended for internal use.

        See _fs_randomPlaylistEntries().
        """
        #debug("---> in _fs_selectRandomPlaylistEntries(%s, builder, %s, %s)" % (path, str(size), str(selectionSize)))
        assert path is not None
        assert builder is not None
        assert size > 0
        assert selectionSize is None or selectionSize >= size
        if selectionSize is None:
            selectionSize = size
        s = set()
        r = None
        rand = random.Random()
        try:
            r = open(path, 'r')
            #debug("    opened '%s' for reading" % path)
            numLines = builder.fs_lineCount()
            #debug("    total number of lines = %i" % numLines)
            inds = set()
            while len(inds) < selectionSize:
                inds.add(rand.randrange(0, numLines))
            inds = list(inds)
            inds.sort()
            inds.reverse()
            #debug("    randomly-selected indices, in reverse order: [%s]" % ", ".join([str(i) for i in inds]))

            # Now 'inds' contains 'selectionSize' unique indices in decreasing
            # order.
            lineIndex = 0
            for line in r:
                if not inds or len(s) == size:
                    break
                if lineIndex == inds[-1]:
                    s.add(line.strip())
                    inds.pop()
                lineIndex += 1
        finally:
            ut.ut_tryToCloseAll(r)
        if len(s) < size:
            #debug("    only %i items were selected: trying again with size = %i" % (len(s), size * 2))
            result = self. \
                _fs_selectRandomPlaylistEntries(path, builder, size,
                                                selectionSize * 2)
            result = result[0:size]
        else:
            #debug("    shuffling a list of the set of items")
            result = list(s)
            rand.shuffle(result)
        assert result is not None
        assert len(result) == size
        return result

    def fs_generateDocumentation(self):
        """
        Generates all of the automatically generated documentation, returning
        True iff it's successful.
        """
        #debug("---> in fs_generateDocumentation()")
        result = False
        p2i = None
        (rawAlbumsDataFile, rawTracksDataFile) = (None, None)
        try:
            try:
                f = _fs_pathnameToInfoShelfFilename
                p2i = _fs_openShelfFile(_fs_metadataDatabaseFilePathname(f))
                (rawAlbumsDataFile, rawTracksDataFile) = \
                    self._fs_buildRawDocumentationDataFiles(p2i)
            finally:
                ut.ut_tryToCloseAll(p2i)
            #debug("    rawAlbumsDataFile = [%s]" % rawAlbumsDataFile)
            if rawAlbumsDataFile is not None:
                assert rawTracksDataFile is not None
                #debug("    generating documentation files ...")
                result = self. \
                    _fs_generateAlbumsDocumentation(rawAlbumsDataFile) and \
                    self._fs_generateTracksDocumentation(rawTracksDataFile)
        finally:
            ut.ut_tryToDeleteAll(rawTracksDataFile, rawAlbumsDataFile)

    def _fs_buildRawDocumentationDataFiles(self, p2i):
        """
        Builds and returns the pathnames of data files containing information
        about all of the original albums and tracks described in 'p2i', a map
        from music file pathnames to 'info' objects describing them.

        The result is a pair whose first item is the pathname of the data
        file containing album information, and whose second item is the
        pathname of the data file containing track information. Each of line
        in both files contains all of the information for one album or track,
        and the pieces of information in a line are in null-separated ('\0')
        fields. The lines in each file are sorted in the order that their
        albums and tracks are to appear in documentation files.

        If one or both of the files was not successfully built then the
        result pair will be (None, None) and whatever files were created will
        have been deleted.
        """
        assert p2i is not None
        result = (None, None)
        (af, tf) = (None, None)
        try:
            (af, tf) = self._fs_buildUnsortedRawDocumentationDataFiles(p2i)
            if ut.ut_sortFileInPlace(af) and ut.ut_sortFileInPlace(tf):
                result = (af, tf)
            else:
                report("    failed to sort one of the raw documentation "
                      "files in place")
        finally:
            if result == (None, None):
                ut.ut_tryToDeleteAll(tf, af)
        assert len(result) == 2
        assert (result[0] is None) == (result[1] is None)
        assert result[0] is None or os.path.isfile(result[0])
        assert result[1] is None or os.path.isfile(result[1])
        return result

    def _fs_buildUnsortedRawDocumentationDataFiles(self, p2i):
        """
        The same as _fs_buildRawDocumentationDataFiles() except that the
        lines in the file whose pathnames are returned aren't sorted.

        See _fs_buildRawDocumentationDataFiles().
        """
        #debug("---> in _fs_buildRawDocumentationDataFiles(%s)" % ut.ut_prettyShortMap(p2i))
        assert p2i is not None
        result = (None, None)
        docDir = _conf.documentationDir
        albumKind = _conf.albumKind
        trackKind = _conf.trackKind
        sep = _fs_rawDocDataFieldSeparator
        af = None
        aw = None
        tf = None
        tw = None
        baseUrl = "file://" + _conf.rootDir
        if not baseUrl.endswith("/"):
            baseUrl += "/"
        try:
            (aw, af) = ut.ut_createTemporaryFile(docDir, "raw-albums-")
            (tw, tf) = ut.ut_createTemporaryFile(docDir, "raw-tracks-")
            baseSubdir = _conf.baseSubdir
            for (p, info) in p2i.items():
                if info.fs_isOriginalFile() and \
                    ut.ut_hasPathnamePrefix(p, baseSubdir):
                    kind = fs_fileKindFromInformation(info)
                    deflt = _fs_defaultDocFieldValue
                    genre = fs_fileGenreFromInformation(info) or deflt
                    tv = lambda t, info = info: info.fs_tagValue(t) or deflt
                    artist = tv(music.mu_flacArtistTag)
                    album = tv(music.mu_flacAlbumTag)
                    date = tv(music.mu_flacDateTag)
                    url = baseUrl + info.fs_pathname()
                    if kind == albumKind:
                        aw.write("%s%s%s%s%s%s%s%s%s\n" % (artist, sep,
                            date, sep, album, sep, genre, sep, url))
                    elif kind == trackKind:
                        title = tv(music.mu_flacTrackTitleTag)
                        tw.write("%s%s%s%s%s%s%s%s%s%s%s\n" % (title, sep,
                            artist, sep, album, sep, date, sep, genre, sep,
                            url))
                    else:
                        report("can't document a music file with unknown "
                               "kind '%s'" % kind)
            result = (af, tf)
        finally:
            ut.ut_tryToCloseAll(aw, tw)
            if result == (None, None):
                ut.ut_tryToDeleteAll(tf, af)
        #debug("    result = %s" % str(result))
        assert len(result) == 2
        assert (result[0] is None) == (result[1] is None)
        assert result[0] is None or os.path.isfile(result[0])
        assert result[1] is None or os.path.isfile(result[1])
        return result

    def _fs_generateAlbumsDocumentation(self, rawDataFile):
        """
        Generates the final documentation file(s) about the albums in our
        main music catalogue from the information in the raw data file with
        pathname 'rawDataFile', returning True iff we're successful.
        """
        #debug("---> in _fs_generateAlbumsDocumentation(%s)" % rawDataFile)
        assert rawDataFile is not None
        assert os.path.isfile(rawDataFile)
        result = False
        r = None
        w = None
        dest = os.path.join(_conf.documentationDir,
                            _fs_albumsDocumentationFilename)
        #debug("   dest = [%s]" % dest)
        try:
            timestamp = time.strftime("%B %d, %Y at %I:%M%P")
            startEndMap = {"docLastUpdatedTimestamp": timestamp}
            r = open(rawDataFile)
            w = open(dest, 'w')
            #debug("    starting to write albums list ...")
            w.write(_conf.docAlbumsHtmlStartFmt % startEndMap)
            sep = _fs_rawDocDataFieldSeparator
            itemFmt = _conf.docAlbumsHtmlItemFmt
            numLines = 0
            for line in r:
                numLines += 1
                (artist, year, title, genre, url) = line.split(sep)
                w.write(itemFmt % {"artist": artist, "releaseDate": year,
                    "title": title, "genre": genre, "url": url})
            startEndMap["albumCount"] = numLines
            w.write(_conf.docAlbumsHtmlEndFmt % startEndMap)
            result = True
            #debug("    finished writing albums list")
        finally:
            ut.ut_tryToCloseAll(r, w)
            if not result:
                ut.ut_tryToDeleteAll(dest)
        return result

    def _fs_generateTracksDocumentation(self, rawDataFile):
        """
        Generates the final documentation file(s) about the tracks in our
        main music catalogue from the information in the raw data file with
        pathname 'rawDataFile', returning True iff we're successful.
        """
        #debug("---> in _fs_generateTracksDocumentation(%s)" % rawDataFile)
        assert rawDataFile is not None
        assert os.path.isfile(rawDataFile)
        result = False
        r = None
        w = None
        dest = os.path.join(_conf.documentationDir,
                            _fs_tracksDocumentationFilename)
        #debug("    dest = [%s]" % dest)
        try:
            timestamp = time.strftime("%B %d, %Y at %I:%M%P")
            startEndMap = {"docLastUpdatedTimestamp": timestamp}
            r = open(rawDataFile)
            w = open(dest, 'w')
            #debug("    starting to write tracks list ...")
            w.write(_conf.docTracksHtmlStartFmt % startEndMap)
            sep = _fs_rawDocDataFieldSeparator
            itemFmt = _conf.docTracksHtmlItemFmt
            numLines = 0
            numHidden = 0
            for line in r:
                numLines += 1
                (title, artist, album, year, genre, url) = line.split(sep)
                isHidden = (title in _fs_trackTitlesToHideInDocs)
                if isHidden:
                    numHidden += 1
                    w.write("\n<!--")
                w.write(itemFmt % {"title": title, "artist": artist,
                    "releaseDate": year, "album": album, "genre": genre,
                    "url": url})
                if isHidden:
                    w.write("\n-->")
            startEndMap["trackCount"] = numLines
            startEndMap["hiddenTrackCount"] = numHidden
            w.write(_conf.docTracksHtmlEndFmt % startEndMap)
            #debug("    finished writing tracks list")
            result = True
        finally:
            ut.ut_tryToCloseAll(r, w)
            if not result:
                ut.ut_tryToDeleteAll(dest)
        return result


    def fs_synchronizeAllRatingsInformation(self):
        """
        Synchronizes all of the ratings information related to all of the
        known ratings files.

        See fs_synchronizeRatingsInformation().
        """
        for base in _conf.allRatingsBasenames:
            self.fs_synchronizeRatingsInformation(base)

    def fs_refreshAllRatingsInformation(self):
        """
        Refreshes all of the ratings information related to all of the
        known ratings files.

        See fs_refreshRatingsInformation().
        """
        for base in _conf.allRatingsBasenames:
            self.fs_refreshRatingsInformation(base)

    def fs_synchronizeRatingsInformation(self, base):
        """
        Synchronizes all of the ratings information related to the ratings in
        the ratings file with base name 'base' so that they all reflect the
        same set of ratings information.

        See fs_synchronizeAllRatingsInformation().
        """
        assert base
        cmd = _fs_refreshRatingsCommandFmt % { "base": base,
                                    "type": _fs_internalRefreshType }
        _fs_sendChangeRatingsCommand(cmd)

    def fs_refreshRatingsInformation(self, base):
        """
        Refreshes all of the ratings information related to the ratings in
        the ratings file with base name 'base' so that they're synchronized
        with each other, and they contain information about all of the audio
        files in the current version of the main music directory catalogue.

        See fs_refreshAllRatingsInformation().
        """
        assert base
        cmd = _fs_refreshRatingsCommandFmt % { "base": base,
                                    "type": _fs_externalRefreshType }
        _fs_sendChangeRatingsCommand(cmd)


    def fs_rebuildCatalogueFile(self, errorOut = None, canBeSlow = False):
        """
        Rebuilds the catalogue file, writing any and all error messages to
        the file/stream object 'errorOut' iff it's not None.

        The default means of rebuilding the catalogue file is to merge all
        of the filesystems' catalogue summary metadata files together. But if
        that fails and 'canBeSlow' is True then an attempt it made to rebuild
        the catalogue from the per-audio file metadata files and/or the
        audio files themselves.

        WARNING: rebuilding a catalogue the slow way can take a LONG time -
        10 hours or more - for fairly large music collections.
        """
        #debug("---> in fs_rebuildCatalogueFile()")
        # 'errorOut' can be None
        catPath = self._fs_cataloguePathname()
        (d, f) = os.path.split(catPath)
        (w, tmpPath) = (None, None)
        try:
            (w, tmpPath) = ut.ut_createTemporaryFile(d, f + "-")
            #debug("    temp catalogue path = [%s]" % tmpPath)
            rootDir = _conf.rootDir
            try:
                #debug("    merging whole catalogue summary metadata files")
                fs_mergeCatalogues(_conf.allMusicFilesystemMountPoints, w)
                #debug("    merge completed successfully")
            except fs_MissingCatalogueException:
                #debug("    one or more summary metadata files missing")
                if canBeSlow:
                    b = fs_SortedMusicDirectoryCatalogueBuilder(rootDir,
                                                                errorOut)
                    b.build(rootDir, w)
                else:
                    raise
            w.close()
            w = None
            os.rename(tmpPath, catPath)

            # Refresh/update all of the files that depend on the catalogue.
            self.fs_refreshAllMetadataFilesFromCatalogue()
        finally:
            ut.ut_tryToCloseAll(w)
            ut.ut_deleteFileOrDirectory(tmpPath)

    def fs_refreshAllMetadataFilesFromCatalogue(self):
        """
        Refreshes all of the metadata files that should be updated when the
        catalogue changes.
        """
        self.fs_refreshAllGeneralMetadataFiles()
        self.fs_refreshAllRatingsInformation()

    def fs_refreshAllGeneralMetadataFiles(self):
        """
        Refreshes all of the general metadata files: that is, the ones
        found in the _conf.metadataDir directory.
        """
        self._fs_refreshPathnameToOriginalPathnameDatabaseFile()
        self._fs_refreshPathnameToInformationDatabaseFile()
        self._fs_refreshSearchDatabaseFile()

    def _fs_refreshPathnameToOriginalPathnameDatabaseFile(self,
                                                          force = False):
        """
        Creates (if it doesn't exist) or updates (if it does exist) the DBM
        file that maps each music file's pathname to the pathname of its
        original file if it isn't original, and to its own pathname if it is
        original.

        The DBM file will always be created or updated if 'force' is True,
        but if 'force' is False - which is the default - then the DBM file
        will only be created or updated if it isn't strictly newer than the
        main music directory catalogue file.
        """
        f = _fs_pathnameToOriginalPathnameDbmFilename
        o2pPath = _fs_metadataDatabaseFilePathname(f)
        catPath = self._fs_cataloguePathname()
        if force or ut.ut_doUpdateFile(o2pPath, catPath):
            m = None
            try:
                m = _fs_openDbmFile(o2pPath, "n")
                b = fs_PathnameToOriginalPathnameMapBuilder(m)
                b.fs_parse(catPath)
            finally:
                ut.ut_tryToCloseAll(m)

    def _fs_refreshPathnameToInformationDatabaseFile(self, force = False):
        """
        Creates (if it doesn't exist) or updates (if it does exist) the DBM
        file that maps each music file's pathname to information about the
        file (as a fs_CataloguedFileInformation object).

        The DBM file will always be created or updated if 'force' is True,
        but if 'force' is False - which is the default - then the DBM file
        will only be created or updated if it isn't strictly newer than the
        main music directory catalogue file.
        """
        f = _fs_pathnameToInfoShelfFilename
        p2iPath = _fs_metadataDatabaseFilePathname(f)
        catPath = self._fs_cataloguePathname()
        if force or ut.ut_doUpdateFile(p2iPath, catPath):
            m = None
            try:
                m = _fs_openShelfFile(p2iPath, "n")
                b = fs_PathnameToInformationMapBuilder(m)
                b.fs_parse(catPath)
            finally:
                ut.ut_tryToCloseAll(m)

    def _fs_refreshSearchDatabaseFile(self, force = False):
        """
        Creates (if it doesn't exist) or updates (if it does exist) the
        sqlite database file that contains information used by the music
        search filesystem, iff a music search filesystem is to be mounted.

        The database file will always be created or updated if 'force' is
        True, but if 'force' is False - which is the default - then the file
        will only be created or updated if it isn't strictly newer than the
        main music directory catalogue file.
        """
        #debug("---> in _fs_refreshSearchDatabaseFile(%s)" % str(force))
        if _conf.isNonemptySearchDirectory():
            #debug("    is non-empty search dir")
            dbPath = fs_searchDatabasePathname()
            catPath = self._fs_cataloguePathname()
            #debug("    db file = [%s], catalogue file = [%s]" % (dbPath, catPath))
            if force or ut.ut_doUpdateFile(dbPath, catPath):
                #debug("    are (re)building search db file ...")
                import musicsearchfs
                    # we do this here to avoid requiring search-specific
                    # dependencies when there's no music search directory
                keys = musicsearchfs.fs_tagsToKeys(_conf.searchableTagNames)
                #debug("    search keys = [%s]" % ", ".join(keys))
                musicsearchfs.fs_rebuildSearchDatabaseFile(dbPath, catPath,
                                                           keys)
                #debug("    finished rebuilding search db file")

    def _fs_cataloguePathname(self):
        """
        Returns the pathname of the music directory catalogue file.
        """
        result = _conf.cataloguePathname
        assert result is not None
        return result

    def _fs_playlistsDirectory(self):
        """
        Returns the pathname of the directory that all of the playlist files
        are located under.
        """
        result = _conf.playlistsDir
        assert result is not None
        return result


class fs_AbstractMusicFilesystem(mergedfs.fs_AbstractMetadataMergedFilesystem):
    """
    An abstract base class for filesystems that convert one type of music
    file into another, caching the resulting generated files.
    """

    def __init__(self, *args, **kw):
        kw["minCacheableDirSize"] = _fs_minCacheableDirSize
        mergedfs.fs_AbstractMetadataMergedFilesystem. \
            __init__(self, *args, **kw)

        # This is supposed to fix problems with corrupted reads of files
        # through these filesystems.
        self.multithreaded = False


    def _fs_isSummaryMetadataFilePathname(self, path):
        #debug("---> in fs_AbstractMusicFilesystem._fs_isSummaryMetadataFilePathname(%s)" % path)
        assert path is not None
        return path in _fs_summaryMetadataFilePathnames

    def _fs_allSummaryMetadataFileDirentries(self):
        """
        Returns a list of Direntry objects that together represent all of
        the files and directories in our summaries metadata directory.
        """
        #debug("---> in fs_AbstractMusicFilesystem._fs_allSummaryMetadataFileDirentries()")
        #assert result is not None
        return _fs_summaryMetadataFileDirentries

    def _fs_generateSummaryMetadataFile(self, path, cachedPath,
                                        finalCachedPath):
        assert path is not None
        assert self._fs_isSummaryMetadataFilePathname(path)
        assert cachedPath is not None
        assert os.path.isabs(cachedPath)
        assert finalCachedPath is not None
        assert os.path.isabs(finalCachedPath)
        bname = os.path.basename(path)
        if bname == _fs_catalogueSummaryMetadataFileBasename:
            result = self._fs_generateCatalogueSummaryMetadataFile(path,
                                                cachedPath, finalCachedPath)
        else:
            raise ValueError("Asked to generate an unknown/unexpected "
                "summary metadata file : [%s]" % path)
        assert result is not None or os.path.lexists(finalCachedPath)
        return result

    def _fs_generateCatalogueSummaryMetadataFile(self, path, cachedPath,
                                                 finalCachedPath):
        """
        Generates - synchronously or asynchronously - a file with absolute
        pathname 'cachedPath' that is the cached version of the catalogue
        summary metadata file (with pathname 'path') for this filesystem,
        and then - iff it's generated asynchronously - renames 'cachedPath'
        to 'finalCachedPath'.

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
        """
        #debug("---> in fs_AbstractMusicFilesystem._fs_generateCatalogueSummaryMetadataFile(%s, %s, %s)" % (path, cachedPath, finalCachedPath))
        assert path is not None
        assert cachedPath is not None
        assert os.path.isabs(cachedPath)
        assert finalCachedPath is not None
        assert os.path.isabs(finalCachedPath)
        (result, wfd) = os.pipe()
        #debug("    creating the metadata file builder ...")
        b = self._fs_createCatalogueSummaryMetadataFileBuilder(_conf.rootDir)
        #debug("    creating the catalogue generating daemon process ...")
        proc = fs_DefaultGenerateCatalogueDaemonProcess(b, wfd, cachedPath,
                                                        finalCachedPath)
        #debug("    did fs_AbstractMusicFilesystem's catalogue summary metadata file generation start? %s" % str(result is not None))
        assert result is not None or os.path.lexists(finalCachedPath)
        return result

    def _fs_createCatalogueSummaryMetadataFileBuilder(self, baseDir):
        """
        Creates and returns the instance of a concrete subclass of
        fs_AbstractSortedMusicDirectoryCatalogueBuilder that is to be used to
        build this filesystem's catalogue summary metadata file.
        """
        assert baseDir is not None
        assert os.path.isabs(baseDir)
        raise NotImplementedError
        #assert result is not None

    def _fs_minimumTemporaryGeneratedFileSize(self):
        """
        Returns the minimum size (in bytes) that a temporary cached file must
        have before we start to read any data from it.
        """
        result = _fs_minTempGeneratedFileSize
        assert result >= 0
        return result

    def _fs_allMetadataFileExtensions(self):
        """
        Returns a list of the extensions for each and every metadata file
        that we (at least potentially) generate for each non-metadata music
        file in this filesystem.
        """
        result = _fs_defaultAllMetadataFileExtensions
        assert result is not None
        return result

    def _fs_isExistingMetadataFilePathname(self, path, origPath):
        #debug("---> in fs_AbstractMusicFilesystem._fs_isExistingMetadataFilePathname(%s, %s)" % (path, origPath))
        assert path is not None
        assert self._fs_isUnderMetadataDirectory(path)
        assert origPath is not None
        assert self._fs_isExistingFile(origPath)
        if self.fs_hasTargetMusicFileFilename(origPath):
            #debug("    it may be a metadata file corresponding to a music file")
            result = False
            for ext in self._fs_allMetadataFileExtensions():
                if mergedfs.fs_doesEndWithMetadataExtension(path, ext):
                    #debug("        metadata file with extension '%s'" % ext)
                    result = True
                    break
        else:
            #debug("    it is a metadata directory")
            result = True
        return result

    def _fs_metadataDirentriesFor(self, origDir, entry):
        #debug("---> in fs_AbstractMusicFilesystem._fs_metadataDirentriesFor(%s, %s)" % (origDir, str(entry)))
        assert origDir is not None
        assert entry is not None
        fname = entry.name
        if self.fs_hasTargetMusicFileFilename(fname):
            #debug("    'entry' represents a non-metadata music file")
            for ext in self._fs_allMetadataFileExtensions():
                #debug("        metadata filename extension = '%s'" % ext)
                name = mergedfs.fs_toFilesMetadataFilename(fname, ext)
                #debug("        yielding Direntry with name = '%s'" % name)
                result = Direntry(name)
                assert result is not None
                yield result
        else:  # we assume it's a directory
            yield entry

    def _fs_metadataFileContents(self, path, origPath):
        #debug("---> in fs_AbstractMusicFilesystem._fs_metadataFileContents(%s, %s)" % (path, origPath))
        assert path is not None
        assert origPath is not None
        result = None
        if mergedfs.fs_doesEndWithMetadataExtension(path,
                                        fs_tagsMetadataFileExtension):
            result = self._fs_tagsMetadataFileContents(origPath)
        elif mergedfs.fs_doesEndWithMetadataExtension(path,
                                        _fs_originsMetadataFileExtension):
            result = self._fs_originsMetadataFileContents(origPath)
        elif mergedfs.fs_doesEndWithMetadataExtension(path, mergedfs.
                                        fs_pathnameMetadataFileExtension):
            result = self._fs_pathnameMetadataFileContents(path, origPath)
        elif mergedfs.fs_doesEndWithMetadataExtension(path,
                                        _fs_derivedMetadataFileExtension):
            result = self._fs_derivedMetadataFileContents(origPath)
        #debug("    result (file contents) = [%s]" % result)
        # 'result' can be None
        return result


    def fs_hasTargetMusicFileFilename(self, f):
        """
        Returns True iff the pathname or filename 'f' is such that it could
        be that of a (non-metadata) music file that appears in this
        filesystem.
        """
        assert f is not None
        raise NotImplementedError

    def _fs_originsMetadataFileContents(self, origPath):
        """
        Returns a string containing the contents of the metadata file that
        contains information about the origins of the non-metadata music file
        with pathname 'origPath', or None if there's no metadata file with
        pathname 'origPath'.

        This method assumes that 'origPath' is relative to our mount point
        (though it starts with a pathname separator).
        """
        assert origPath is not None
        raise NotImplementedError
        # 'result' can be None

    def _fs_tagsMetadataFileContents(self, origPath):
        """
        Returns a string containing the contents of the metadata file that
        contains the names and values of all of the tags in the non-metadata
        music file with pathname 'origPath', or None if there's no metadata
        file with pathname 'origPath'.

        This method assumes that 'origPath' is relative to our mount point
        (though it starts with a pathname separator).
        """
        assert origPath is not None
        raise NotImplementedError
        # 'result' can be None

    def _fs_derivedMetadataFileContents(self, origPath):
        """
        Returns a string containing the contents of the metadata file that
        contains information derived from the non-metadata music file with
        pathname 'origPath' itself, or returns None if there's no metadata
        file with pathname 'origPath'.

        This method assumes that 'origPath' is relative to our mount point
        (though it starts with a pathname separator).
        """
        assert origPath is not None
        raise NotImplementedError
        # 'result' can be None


    # Utility methods.

    def _fs_buildDerivedMetadataFileContentsFromFile(self, realPath):
        """
        Builds and returns a string containing the contents of the derived
        metadata file corresponding to the real audio file with pathname
        'realPath'.
        """
        assert realPath is not None
        secs = music.mu_durationInSeconds(realPath)
        result = self._fs_buildDerivedMetadataFileContentsFromData(secs)
        assert result is not None  # though it may be empty
        return result

    def _fs_buildDerivedMetadataFileContentsFromData(self,
                                                     durationInSeconds):
        """
        Builds and returns a string containing the contents of the derived
        metadata file containing the specified information.
        """
        assert durationInSeconds == -1 or durationInSeconds >= 0
        if durationInSeconds < 0:
            result = ""
        else:
            m = _fs_buildDerivedMetadataMap(durationInSeconds)
            result = mergedfs.fs_tagsMapToMetadataFileContents(m)
        assert result is not None  # though it may be empty
        return result


    def _fs_trackNumberFromFilename(self, trackFilename):
        """
        Returns the track number corresponding to the single-track FLAC
        file with basename 'trackFilename', or zero (0) if it can't be
        obtained.

        Note: a single-track FLAC file's basename must start with its
        track number, possibly padded to the left with zeroes (0), and
        followed by an underscore.
        """
        result = 0
        i = trackFilename.find(_fs_trackNumberTerminator)
        if i > 0:
            num = trackFilename[0:i]
            if num.isdigit():
                result = ut.ut_tryToParseInt(num, 0, minValue = 1)
        assert result >= 0
        return result

    def _fs_simplifyFilename(self, filename):
        """
        Returns a simplified version of the base filename 'filename':
        "unusual" characters are transformed or removed, and the filename
        is kept to a reasonable length.

        'filename' is assumed not to have any path components (and thus
        no pathname separators or anything that we have to avoid mangling).
        It also won't mangle any file extensions so long as they consist of
        only alphanumeric characters after the '.'.
        """
        #debug("---> in _fs_simplifyFilename(%s)" % filename)
        assert filename is not None
        assert len(filename) > 0
        chars = []
        maxChars = _fs_maxCharsInSimplifiedFilename
        for ch in filename:
            if ch == "/" or ch == "|":
                chars += ","
            elif ch.isalnum() or ch in ".,;:=+-_()[]":
                chars += ch
            # else discard 'ch'
            if len(chars) >= maxChars:
                break
        if chars[0] == ".":
            chars[0] = ","  # don't create hidden filenames
        result = "".join(chars)
        if len(result) == 0:
            result = "x" * len(filename)  # default non-empty result
        #debug("    result = [%s]" % result)
        assert result is not None
        assert len(result) > 0
        return result


class fs_FlacReencodingCommandDaemonProcess(mergedfs.fs_GenerateFileFromCommandDaemonProcess):
    """
    Represents a daemon process used to reencode a FLAC file into an audio
    file of a different format by executing a shell command.
    """

    def __init__(self, flacPath, cmd, rfd, wfd, tmpPath, finalPath, doDebug = False):
        """
        Initializes us with the pathname of the FLAC file we'll be
        reencoding, the shell command 'cmd' to executeto do the reencoding,
        the pipe's readable and writable file descriptors ('rfd' and 'wfd',
        respectively), the pathname 'tmpPath' of the file we generate while
        we're generating it, and the pathname 'finalPath' that 'tmpPath'
        will be renamed to if/when it's fully and successfully generated.
        """
        #debug("---> in fs_FlacReencodingCommandDaemonProcess.__init__(%s, %s, %s, %s, %s, %s)" % (flacPath, cmd, str(rfd), str(wfd), str(tmpPath), str(finalPath)))
        assert flacPath is not None
        assert cmd
        assert rfd
        assert wfd
        assert tmpPath is not None
        assert finalPath is not None
        self._fs_flacPath = flacPath
        mergedfs.fs_GenerateFileFromCommandDaemonProcess.__init__(self, cmd, rfd, wfd, tmpPath, finalPath, doDebug)

    def _ut_run(self):
        #debug("---> in fs_FlacReencodingCommandDaemonProcess._ut_run()")
        # Preload the FLAC file first and wait until it exists, and only then
        # reencode it.
        flacPath = self._fs_flacPath
        #debug("    flacPath = [%s]; preloading it first ..." % flacPath)
        ut.ut_preloadFiles([flacPath])
        #debug("    preloaded the FLAC file")
        while ut.ut_fileSize(flacPath) <= 0:
            #debug("    wait a few (more) seconds for the FLAC file to be non-empty ...")
            time.sleep(3)
        #debug("    FLAC file size = %i" % ut.ut_fileSize(flacPath))
        #debug("    calling our superclass' _ut_run() method to reencode the FLAC file")
        mergedfs.fs_GenerateFileFromCommandDaemonProcess._ut_run(self)

class _fs_GetBasedirFromCatalogueContentHandler(xml.sax.ContentHandler):
    """
    The class of SAX content handler that extracts from a music catalogue file the
    value of the 'basedir' attribute on the top-level 'catalogue' element.

TODO: it seems like there should be an easier way to do this that doesn't involve
parsing the whole catalogue (or loading it all into memory): is there ???!!!!????
- is there some way to signal the SAX parser that we don't need to process the
  rest of the file?
    """

    def __init__(self):
        xml.sax.ContentHandler.__init__(self)
        self.basedir = None

    def startElement(self, name, attrs):
        if name == _fs_catalogueElementName and self.basedir is None:
            self.basedir = attrs.get(_fs_baseDirAttributeName)
        # ignore all other elements

class _fs_FlacReencodingMetadataCatalogueExploder(fs_MusicDirectoryCatalogueExploder):
    """
    The class of fs_MusicDirectoryCatalogueExploder that explodes a catalogue
    that is assumed to contain only entries describing FLAC album and track
    files, but only after transforming the FLAC track entries to reflect the
    corresponding re-encoded files (and omitting the album entries).
    """

    def __init__(self, destDir, fs, relDir):
        """
        Initializes us with the pathname 'destDir' of the directory to
        explode the catalogue file out into, the
        fs_AbstractFlacReencodingFilesystem 'fs' that we're exploding the
        catalgoue file for, and the pathname 'relDir' of the directory
        (relative to its mount point) of the directory under which the
        re-encoded files are found.
        """
        #debug("---> in _fs_FlacReencodingMetadataCatalogueExploder.__init__(%s, fs, %s)" % (destDir, relDir))
        assert destDir is not None
        assert os.path.isabs(destDir)
        assert os.path.isdir(destDir)
        assert fs is not None
        assert relDir is not None
        assert not os.path.isabs(relDir)
        fs_MusicDirectoryCatalogueExploder.__init__(self, destDir)
        self._fs_filesystem = fs
        self._fs_relFlacTracksDir = None
        self._fs_relDir = relDir

    def _fs_transformFileInformation(self, info):
        #debug("---> in _fs_transformFileInformation(info)")
        path = info.fs_pathname()
        relFlacDir = self._fs_relativeFlacTracksDirectory()
        if ut.ut_hasPathnamePrefix(path, relFlacDir):
            #debug("    is info for track file [%s]" % path)
            newPath = self._fs_transformTrackPathname(path)
            info.fs_setPathname(newPath)
            #debug("    set new pathname to [%s]" % newPath)
            #debug("    replacing the FLAC file's origins metadata with the re-encoded file's")
            catName = _fs_originsMetadataCategoryName
            info.fs_removeAllCategoryItems(catName)
            info.fs_addCategoryItem(catName, fs_originalOriginsTagName, path)
            #debug("    origins metadata replaced")
            result = info
        else:
            #debug("    is info for non-track (album?) file [%s]" % path)
            result = None  # since 'info' doesn't describe a track file
        # 'result' may be None
        return result

    def _fs_transformTrackPathname(self, path):
        """
        Returns the result of transforming the pathname 'path' of a FLAC
        track file into the pathname of the file that it will be re-encoded
        into.
        """
        #debug("---> in _fs_transformTrackPathname(%s)" % path)
        assert path is not None

        # Replace the FLAC directory with the re-encoded file's directory.
        relFlacDir = self._fs_relativeFlacTracksDirectory()
        result = ut.ut_removePathnamePrefix(path, relFlacDir)
        result = os.path.join(self._fs_relDir, result)
        #debug("    after replacing dir, path = [%s]" % result)

        # Replace the .flac extension with the re-encoded file's extension.
        (base, ext) = os.path.splitext(result)
        assert ext == music.mu_fullFlacExtension
        result = self._fs_filesystem.fs_addTargetMusicFileExtension(base)
        #debug("    after replacing extension, path = [%s]" % result)
        assert result is not None
        return result

    def _fs_relativeFlacTracksDirectory(self):
        #debug("---> in _fs_relativeFlacTracksDirectory()")
        result = self._fs_relFlacTracksDir
        if result is None:
            #debug("    _fs_relFlacTracksDir field not set yet")
            b = self._fs_catalogueBaseDirectory()
            #debug("   basedir from FLAC catalogue: [%s]" % b)
            flacDir = self._fs_filesystem.fs_flacDirectory()
            result = ut.ut_removePathnamePrefix(flacDir, b)
            #debug("    rel. flac tracks dir = [%s]" % result)
            self._fs_relFlacTracksDir = result
        assert result is not None
        return result

class _fs_FlacReencodingMetadataCatalogueBuilder(fs_AbstractSortedMusicDirectoryCatalogueBuilder):
    """
    The class of builder to use to build the catalogue summary metadata file
    for fs_AbstractFlacReencodingFilesystem subclasses.
    """

    def __init__(self, fs, baseDir, errorOut = None):
        """
        Intializes us with the fs_AbstractFlacReencodingFilesystem 'fs' whose
        catalogue metadata summary file we'll be building, the pathname
        'baseDir' of the directory to which all of the pathnames in the
        catalogue we're building will be relative, and the file/stream
        'errorOut' to which to write information about any errors or
        potential problems encountered while building catalogues. (No such
        messages will be written if 'errorOut' is None.)
        """
        #debug("---> in _fs_FlacReencodingMetadataCatalogueBuilder.__init__(fs, %s, errorOut)" % baseDir)
        assert fs is not None
        assert baseDir is not None
        # 'errorOut' may be None
        fs_AbstractSortedMusicDirectoryCatalogueBuilder. \
            __init__(self, baseDir, errorOut)
        self._fs_filesystem = fs

    def _fs_buildDirectoryTree(self):
        #debug("---> in _fs_FlacReencodingMetadataCatalogueBuilder._fs_buildDirectoryTree()")
        # First explode the flactrack filesystem's catalogue metadata file:
        # we do this rather than process that file so that we don't have to
        # deal with its 'directory' elements, which could be problematic.
        fs = self._fs_filesystem
        tmpDir = self._fs_temporaryDirectory()
        #debug("   tmp dir = [%s]" % tmpDir)
        flacDir = fs.fs_flacDirectory()
        #debug("   flac dir = [%s]" % flacDir)
        flacCatalogue = _fs_relativeCatalogueSummaryMetadataFilePathname
        #debug("   rel. flac catalogue pathname = [%s]" % flacCatalogue)
        flacCatalogue = os.path.join(flacDir, flacCatalogue)
        #debug("   abs. flac catalogue pathname = [%s]" % flacCatalogue)
        relDir = self._fs_baseDirectory()
        relDir = ut.ut_removePathnamePrefix(fs.fs_mountDirectory(), relDir)
        #debug("    creating FLAC catalogue file exploder ...")
        p = _fs_FlacReencodingMetadataCatalogueExploder(tmpDir, fs, relDir)
        #debug("    exploding FLAC catalogue file into files for re-encoded tracks")
        p.fs_parse(flacCatalogue)
        #debug("    adding element file for each 'real' track file")
        self._fs_buildRealDirectoryTreePartFor(fs.fs_realFilesDirectory(),
                                                relDir)
        ut.ut_deleteAllEmptyDirectoriesUnder(tmpDir)
            # which removes any and all leftover 'flac' directories

    def _fs_buildRealDirectoryTreePartFor(self, path, relPath):
        """
        Builds the part(s) of our directory tree corresponding to the file
        with pathname 'path' (which is assumed to be in a directory of "real"
        files), and - if it's a directory - all of the files under it.
        Directory tree files will contain pathnames starting with 'relPath'.
        """
        #debug("---> in _fs_FlacReencodingMetadataCatalogueBuilder._fs_buildRealDirectoryTreePartFor(%s, %s)" % (path, relPath))
        assert path is not None  # may be file or directory
        assert os.path.isabs(path)
        assert relPath is not None
        assert not os.path.isabs(relPath)
        if self._fs_isExcludedNonMetadataDir(path):
            pass
        elif os.path.isdir(path):
            join = os.path.join
            for f in os.listdir(path):
                self._fs_buildRealDirectoryTreePartFor(join(path, f),
                                                       join(relPath, f))
        elif os.path.exists(path) and \
             self._fs_filesystem.fs_hasTargetMusicFileFilename(path):
            self._fs_addFileForRealFile(path, relPath)
        else:
            #debug("    ignoring file [%s] under real files dir" % path)
            pass

    def _fs_addFileForRealFile(self, path, relPath):
        """
        Adds a file to our directory tree for the "real" audio file with
        pathname 'path'. The file's pathname in the file we're adding will be
        'relPath'.
        """
        #debug("---> in _fs_FlacReencodingMetadataCatalogueBuilder._fs_addFileForRealFile(%s, %s)" % (path, relPath))
        assert path is not None
        assert os.path.isabs(path)
        assert relPath is not None
        assert not os.path.isabs(relPath)
        self._fs_writeRealFileDirectoryTreeFile(path, relPath)
        #debug("    done adding file for real file [%s] ([%s])" % (relPath, path))

class fs_AbstractFlacReencodingFilesystem(fs_AbstractMusicFilesystem):
    """
    An abstract base class for filesystems that convert FLAC audio files into
    audio files of another format, caching the resulting generated files.

    Note: there will be a one-to-one mapping from the FLAC files to the audio
    files in the other format: a FLAC file with pathname
    '$flacDir/some/dirs/name.flac' will generate an audio file with a pathname
    like '$mountDir/some/dirs/name.someExt', where 'someExt' is a file
    extension appropriate to the format of the generated audio file.
    """

    def __init__(self, *args, **kw):
        fs_AbstractMusicFilesystem.__init__(self, *args, **kw)
        self._fs_flacDir = None

    def fs_processOptions(self, opts):
        fs_AbstractMusicFilesystem.fs_processOptions(self, opts)
        val = fscommon.fs_parseRequiredSuboption(opts, fs_flacDirOption)
        self._fs_flacDir = ut.ut_expandedAbsolutePathname(val)

    def fs_flacDirectory(self):
        """
        Returns the absolute pathname of the directory under which the
        FLAC files are located.
        """
        result = self._fs_flacDir
        assert result is not None
        assert os.path.isabs(result)
        return result

    def _fs_generateDirectoryEntryNames(self, path):
        #debug("---> in fs_AbstractFlacReencodingFilesystem._fs_generateDirectoryEntryNames(%s)" % path)
        assert path is not None
        d = fscommon.fs_pathnameRelativeTo(self.fs_flacDirectory(), path)
        #debug("    d = [%s]" % d)
        if os.path.isdir(d):
            #debug("        (which is a directory)")
            for f in os.listdir(d):
                #debug("    examining entry '%s' ..." % f)
                if os.path.isdir(os.path.join(d, f)):
                    #debug("        it's a directory: returning it")
                    yield f
                elif music.mu_hasFlacFilename(f):
                    (base, ext) = os.path.splitext(f)
                    #debug("        (base, ext) = (%s, %s)" % (base, ext))
                    result = self.fs_addTargetMusicFileExtension(base)
                    #debug("        yielding target file [%s]" % result)
                    yield result

    def _fs_generateFile(self, path, cachedPath, finalCachedPath):
        #debug("---> in fs_AbstractFlacReencodingFilesystem._fs_generateFile(%s, %s, %s)" % (path, cachedPath, finalCachedPath))
        assert path is not None
        assert os.path.isabs(cachedPath)
        assert finalCachedPath is not None
        assert os.path.isabs(finalCachedPath)
        result = None
        doGenerate = True
        if self.fs_hasTargetMusicFileFilename(path):
            #debug("    'path' has target audio file filename")
            flacPath = self._fs_targetToFlacFilePathname(path)
            #debug("    flacPath = [%s]" % flacPath)
            if ut.ut_isExistingRegularFile(flacPath):
                #debug("    'flacPath' is an existing regular file")
                doGenerate = False
                result = self._fs_createTargetFileFromFlacFile(flacPath,
                                            cachedPath, finalCachedPath)
                if result is None:
# TODO: is there a better class of exception to throw here ???!!!!???
                    raise ValueError("failed to start asynchronously "
                        "generating the cached file '%s' that's a "
                        "reencoding of the FLAC file '%s'" %
                        (finalCachedPath, flacPath))
        if doGenerate:
            # See if we need to generate a directory instead.
            #debug("    not generating (or failed to generate) an MP3")
            f = fscommon.fs_pathnameRelativeTo(self.fs_flacDirectory(), path)
            if os.path.isdir(f):
                #debug("    generating a directory for FLAC dir [%s]" % f)
                doGenerate = False
                self._fs_createGeneratedDirectory(cachedPath)
        # 'result' may be None
        return result

    def _fs_generatedFileOriginFilePathname(self, path):
        #debug("---> in fs_AbstractFlacReencodingFilesystem._fs_generatedFileOriginFilePathname(%s)" % path)
        assert path is not None
        result = None
        if self.fs_hasTargetMusicFileFilename(path):
            f = self._fs_targetToFlacFilePathname(path)
        else:
            f = fscommon.fs_pathnameRelativeTo(self.fs_flacDirectory(), path)
        #debug("    f = [%s]" % f)
        if os.path.lexists(f):
            #debug("the origin file for '%s' is '%s'" % (path, f))
            result = f
        #debug("    result = [%s]" % result)
        # 'result' may be None
        return result

    def _fs_createCatalogueSummaryMetadataFileBuilder(self, baseDir):
        assert baseDir is not None
        assert os.path.isabs(baseDir)
        #debug("**** fs_AbstractFlacReencodingFilesystem._fs_createCatalogueSummaryMetadataFileBuilder(%s)" % baseDir)
        #assert result is not None
        return _fs_FlacReencodingMetadataCatalogueBuilder(self, baseDir)

    def _fs_originsMetadataFileContents(self, origPath):
        # Overrides version in fs_AbstractMusicFilesystem.
        #debug("---> in fs_AbstractFlacReencodingFilesystem._fs_originsMetadataFileContents(%s)" % origPath)
        assert origPath is not None
        lines = []
        real = self.fs_realFilePathname(origPath)
        if real is not None:
            #debug("    real path = [%s]" % value)
            lines.append(mergedfs.
                fs_tagMetadataFileLine(fs_realOriginalOriginsTagName, real))
        elif self.fs_hasTargetMusicFileFilename(origPath):
            assert real is None
            #debug("    has target audio file filename")
            value = self._fs_targetToFlacFilePathname(origPath)
            if value is not None:
                lines.append(mergedfs.
                    fs_tagMetadataFileLine(fs_originalOriginsTagName, value))
        result = mergedfs.fs_linesToMetadataFileContents(lines)
        #debug("    result = [%s]" % result)
        # 'result' can be None
        return result

    def _fs_tagsMetadataFileContents(self, origPath):
        # Overrides version in fs_AbstractMusicFilesystem.
        assert origPath is not None
        #debug("---> in fs_AbstractFlacReencodingFilesystem._fs_tagsMetadataFileContents(%s)" % origPath)
        result = {}
        realPath = self.fs_realFilePathname(origPath)
        if realPath is not None and \
           self.fs_hasTargetMusicFileFilename(realPath):
            result = self._fs_realFileTagsMetadataFileContents(realPath)
        elif self.fs_hasTargetMusicFileFilename(origPath):
            # Use the corresponding FLAC file's tags.
            #debug("    has target audio file filename")
            flacPath = self._fs_targetToFlacFilePathname(origPath)
            #debug("    FLAC file pathname = [%s]" % flacPath)
            metaPath = mergedfs.fs_toFilesMetadataPathname(flacPath,
                                            fs_tagsMetadataFileExtension)
            #debug("    FLAC tags metadata file pathname = [%s]" % metaPath)
            if metaPath is not None and os.path.lexists(metaPath):
                #debug("    FLAC tags metadata file exists")
                lines = ut.ut_readFileLines(metaPath)
                result = mergedfs.fs_linesToMetadataFileContents(lines)
        else:  # other files/dirs have no tags metadata
            #debug("    file has no tags metadata")
            result = None
        #debug("    result = [%s]" % result)
        # 'result' can be None
        return result

    def _fs_derivedMetadataFileContents(self, origPath):
        # Overrides version in fs_AbstractMusicFilesystem.
        assert origPath is not None
        #debug("---> in fs_AbstractFlacReencodingFilesystem._fs_derivedMetadataFileContents(%s)" % origPath)
        realPath = self.fs_realFilePathname(origPath)
        if realPath is not None and \
           self.fs_hasTargetMusicFileFilename(realPath):
            result = self. \
                _fs_buildDerivedMetadataFileContentsFromFile(realPath)
        elif self.fs_hasTargetMusicFileFilename(origPath):
            # Use the corresponding FLAC file's derived metadata.
# TODO: we may not be able to just copy the FLAC file's derived metadata
# if/when we add more types of derived metadata !!!!
            #debug("    has target audio file filename")
            flacPath = self._fs_targetToFlacFilePathname(origPath)
            #debug("    FLAC file pathname = [%s]" % flacPath)
            metaPath = mergedfs.fs_toFilesMetadataPathname(flacPath,
                                            _fs_derivedMetadataFileExtension)
            #debug("    FLAC tags metadata file pathname = [%s]" % metaPath)
            if metaPath is not None and os.path.lexists(metaPath):
                #debug("    FLAC tags metadata file exists")
                lines = ut.ut_readFileLines(metaPath)
                result = mergedfs.fs_linesToMetadataFileContents(lines)
        else:  # other files/dirs have no tags metadata
            #debug("    file has no tags metadata")
            result = None
        #debug("    result = [%s]" % result)
        # 'result' can be None
        return result

    def _fs_targetToFlacFilePathname(self, path):
        """
        Returns the pathname of the FLAC file that the target audio file with
        pathname 'path' is an encoding of.
        """
        assert path is not None
        assert self.fs_hasTargetMusicFileFilename(path)
        (base, ext) = os.path.splitext(path)
        result = fscommon.fs_pathnameRelativeTo(self.fs_flacDirectory(),
                                            music.mu_addFlacExtension(base))
        assert result is not None
        return result


    def fs_addTargetMusicFileExtension(self, base):
        """
        Returns the result of adding to 'base' the file extension for the
        type of audio file that this filesystem generates.
        """
        assert base is not None
        raise NotImplementedError
        # assert result is not None

    def _fs_createTargetFileFromFlacFile(self, flacPath, cachedPath,
                                         finalCachedPath):
        """
        Asynchronously generates the target audio file with (temporary)
        pathname 'cachedPath' from the FLAC audio file with pathname
        'flacPath', then - iff 'cachedPath' is fully successfully generated -
        renames 'cachedPath' to 'finalCachedPath'.

        Returns a readable file descriptor from which can be read the file's
        contents as they're generated, or returns None if asynchronous file
        generation couldn't be started.
        """
        #debug("---> in fs_AbstractFlacReencodingFilesystem._fs_createTargetFileFromFlacFile(%s, %s, %s)" % (flacPath, cachedPath, finalCachedPath))
        assert flacPath is not None
        assert ut.ut_isExistingRegularFile(flacPath)
        assert cachedPath is not None
        assert finalCachedPath is not None
        cmd = self._fs_writeReencodedFileContentsShellCommand(flacPath)
        (result, wfd) = os.pipe()

        #debug("    about to create an fs_FlacReencodingCommandDaemonProcess ...")
        proc = fs_FlacReencodingCommandDaemonProcess(flacPath, cmd,
                                result, wfd, cachedPath, finalCachedPath)
        # 'result' may be None (at least in theory)
        return result

    def _fs_writeReencodedFileContentsShellCommand(self, flacPath):
        """
        Returns a string containing the shell command (line) that outputs
        on its standard output the contents of the file in this filesystem
        that is a reencoding of the FLAC file with pathname 'flacPath.
        """
        assert flacPath is not None
        raise NotImplementedError
        #assert result is not None
        #return result


    def _fs_realFileTagsMetadataFileContents(self, realPath):
        """
        Returns the contents of the tags metadata file for the target audio
        file corresponding to the audio file with pathname 'realPath' under
        our "real" audio files directory.

        Note: regardless of the names and formats of tags for the target
        audio files, the contents of a tags metadata file uses the tag names
        and formats for FLAC audio files.
        """
        assert realPath is not None
        raise NotImplementedError
        #assert result is not None
