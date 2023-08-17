# Defines a class that implements a FUSE filesystem that contains the result
# of merging the files under an optional "real" directory and FLAC audio
# files that represent the individual tracks of the albums represented by
# FLAC and CUE files under another directory.
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

import musicfs
import music
import mergedfs
from fscommon import debug, report, warn
import fscommon
import utilities as ut
import config

from fuse import Direntry


# Constants.

_conf = config.obtain()

# Option names.
fs_albumDirOption = "albums"

# The low and high sizes of the album and track information cache used by
# each fs_FlacTrackFilesystem.
_fs_lowAlbumCacheSize = 40
_fs_highAlbumCacheSize = 60


# Classes.

class _fs_MetadataCatalogueBuilder(musicfs.fs_AbstractSortedMusicDirectoryCatalogueBuilder):
    """
    The class of builder to use to build an fs_FlacTrackFilesystem's catalogue
    summary metadata file.
    """

    def __init__(self, fs, baseDir, errorOut = None):
        """
        Intializes us with the fs_FlacTrackFilesystem filesystem 'fs' whose
        catalogue metadata summary file we'll be building, the pathname
        'baseDir' of the directory to which all of the pathnames in the
        catalogue we're building will be relative, and the file/stream
        'errorOut' to which to write information about any errors or
        potential problems encountered while building catalogues. (No such
        messages will be written if 'errorOut' is None.)
        """
        #debug("---> in _fs_MetadataCatalogueBuilder.__init__(fs, %s)" % baseDir)
        assert fs is not None
        assert baseDir is not None
        # 'errorOut' may be None
        musicfs.fs_AbstractSortedMusicDirectoryCatalogueBuilder. \
            __init__(self, baseDir, errorOut)
        self._fs_filesystem = fs

    def _fs_buildDirectoryTree(self):
        #debug("---> in _fs_MetadataCatalogueBuilder._fs_buildDirectoryTree()")
        fs = self._fs_filesystem
        rem = ut.ut_removePathnamePrefix
        baseDir = self._fs_baseDirectory()
        relMountDir = rem(fs.fs_mountDirectory(), baseDir)
        assert relMountDir is not None
        albumsDir = fs.fs_albumDirectory()          # abs pathname
        relAlbumsDir = rem(albumsDir, baseDir)
        assert relAlbumsDir is not None
        realTracksDir = fs.fs_realFilesDirectory()  # abs pathname

        # We build the parts from album files first and then the parts from
        # "real" track files because real track files override/replace any
        # that are derived from album files.
        self._fs_buildAlbumDirectoryTreePartFor(albumsDir, relAlbumsDir,
                                                relMountDir)
        self._fs_buildTrackDirectoryTreePartFor(realTracksDir, relMountDir)
        #debug("    at the end of _fs_MetadataCatalogueBuilder._fs_buildDirectoryTree()")

    def _fs_buildAlbumDirectoryTreePartFor(self, path, relAlbumsPath,
                                           relTracksPath):
        """
        Builds the part(s) of our directory tree corresponding to the file
        with pathname 'path' (which is assumed to be in a directory of album
        FLAC (and CUE) files), and - if it's a directory - all of the files
        under it. Directory tree files that represent whole albums will
        contain pathnames starting with 'relAlbumsPath', and those that
        represent tracks from albums will contain pathnames starting with
        'relTracksPath'.
        """
        #debug("---> in _fs_MetadataCatalogueBuilder._fs_buildAlbumDirectoryTreePartFor(%s, %s, %s)" % (path, relAlbumsPath, relTracksPath))
        assert path is not None  # may be file or directory
        assert os.path.isabs(path)
        assert relAlbumsPath is not None
        assert not os.path.isabs(relAlbumsPath)
        assert relTracksPath is not None
        assert not os.path.isabs(relTracksPath)
        if self._fs_isExcludedNonMetadataDir(path):
            #debug("    is excluded non-metadata dir")
            pass
        elif os.path.isdir(path):
            #debug("    is directory")
            join = os.path.join
            for f in os.listdir(path):
                #debug("    building tree part for subdir/file '%s'" % f)
                if music.mu_hasFlacFilename(f):
                    base = os.path.splitext(f)[0]
                else:
                    base = f
                self._fs_buildAlbumDirectoryTreePartFor(join(path, f),
                        join(relAlbumsPath, f), join(relTracksPath, base))
        elif os.path.exists(path) and music.mu_hasFlacFilename(path):
            #debug("    is FLAC file")
            cuePath = self._fs_existingCueFilePathname(path)
            if cuePath is not None:
                #debug("    with corresponding CUE file [%s]" % cuePath)
                # Add entries for the album FLAC file as well as the track
                # FLAC files corresponding to each of its tracks.
                self._fs_addFileForAlbum(path, cuePath, relAlbumsPath)
                self._fs_addFilesForAllAlbumTracks(path, cuePath,
                                               relAlbumsPath, relTracksPath)
            else:
                warn("ignoring album file [%s] with no existing CUE file" % path)
        else:
            #debug("    ignoring file [%s] under albums dir" % path)
            pass

    def _fs_buildTrackDirectoryTreePartFor(self, path, relTracksPath):
        """
        Builds the part(s) of our directory tree corresponding to the file
        with pathname 'path' (which is assumed to be in a directory of "real"
        track FLAC files), and - if it's a directory - all of the files
        under it. Directory tree files will contain pathnames starting with
        'relTracksPath'.
        """
        #debug("---> in _fs_MetadataCatalogueBuilder._fs_buildTrackDirectoryTreePartFor(%s, %s)" % (path, relTracksPath))
        assert path is not None  # may be file or directory
        assert os.path.isabs(path)
        assert relTracksPath is not None
        assert not os.path.isabs(relTracksPath)
        if self._fs_isExcludedNonMetadataDir(path):
            pass
        elif os.path.isdir(path):
            join = os.path.join
            for f in os.listdir(path):
                self._fs_buildTrackDirectoryTreePartFor(join(path, f),
                                                    join(relTracksPath, f))
        elif os.path.exists(path) and music.mu_hasFlacFilename(path):
            self._fs_addFileForRealTrack(path, relTracksPath)
        else:
            warn("ignoring the file [%s] under the real tracks directory" % path)

    def _fs_existingCueFilePathname(self, albumPath):
        """
        Returns the pathname of the CUE file associated with the album FLAC
        file with pathname 'albumPath' if such a CUE file exists, and returns
        None otherwise.
        """
        result = self._fs_filesystem.fs_pathnameForCueFileForAlbum(albumPath)
        if not ut.ut_isExistingRegularFile(result):
            result = None
        # 'result' may be None
        return result

    def _fs_addFileForAlbum(self, albumPath, cuePath, relPath):
        """
        Adds a file to our directory tree for the album (but NOT for its
        tracks: that's done elsewhere) represented by the FLAC and CUE files
        with pathnames 'albumPath' and 'cuePath', respectively. The album
        file's pathname in the file we're adding will be 'relPath'.
        """
        #debug("---> in flactrackfs._fs_MetadataCatalogueBuilder._fs_addFileForAlbum(%s, %s, %s)" % (albumPath, cuePath, relPath))
        assert albumPath is not None
        assert os.path.isabs(albumPath)
        assert cuePath is not None
        assert os.path.isabs(cuePath)
        assert relPath is not None
        assert not os.path.isabs(relPath)
        self._fs_writeRealFileDirectoryTreeFile(albumPath, relPath)

    def _fs_addFilesForAllAlbumTracks(self, albumPath, cuePath,
                                      relAlbumPath, relTracksDir):
        """
        Adds files to our directory tree for each and every track on the
        album represented by the FLAC and CUE files with pathnames
        'albumPath' and 'cuePath', respectively. Each track's pathname in the
        added files will start with 'relTracksDir', and its album's pathname
        will be 'relAlbumPath' in those added files.
        """
        #debug("---> in flactrackfs._fs_MetadataCatalogueBuilder._fs_addFilesForAllAlbumTracks(%s, %s, %s, %s)" % (albumPath, cuePath, relAlbumPath, relTracksDir))
        assert albumPath is not None
        assert os.path.isabs(albumPath)
        assert cuePath is not None
        assert os.path.isabs(cuePath)
        assert relAlbumPath is not None
        assert not os.path.isabs(relAlbumPath)
        assert relTracksDir is not None
        assert not os.path.isabs(relTracksDir)
        #debug("    getting track info ...")
        info = music.mu_allAlbumTrackInformation(albumPath, cuePath)
        perTrackSecs = music. \
            mu_allFlacAlbumTracksDurationsInSeconds(albumPath, cuePath)
        #debug("perTrackSecs = [%s]" % ", ".join([str(x) for x in perTrackSecs]))
        #debug("    ... got track info and durations")
        if info is not None and perTrackSecs is not None:
            #debug("    track info isn't None")
            fs = self._fs_filesystem
            relCuePath = fs.fs_pathnameForCueFileForAlbum(relAlbumPath)
            #debug("    relCuePath = [%s]" % relCuePath)
            fmt = musicfs.fs_buildCatalogueFileElementFormatForAlbumTracks(
                albumPath, cuePath, relAlbumPath, relCuePath, relTracksDir)
            #debug("    fmt = [%s]" % fmt)
            num2str = music.mu_formatTrackNumber
            join = os.path.join
            #debug("    processing each track:")
            quote = ut.ut_quoteForXml
            i = 0
            for (num, title, artist) in info:
                numStr = num2str(num)
                #debug("        track %i: %s by %s" % (num, title, artist))
                fname = fs.fs_buildFilenameOfTrackNumber(num, title, artist)
                #debug("        filename = [%s]" % fname)
                path = join(relTracksDir, fname)
                #debug("        path = [%s]" % path)
                secs = perTrackSecs[i]
                if secs >= 0:
                    contents = fmt % {
                        "basename": quote(fname),
                        "title": quote(title),
                        "artist": quote(artist),
                        "trackNumber": quote(numStr),
                        "durationInSeconds": quote(str(secs))
                    }
                    #debug("        contents = [%s]" % contents)
                    self._fs_writeFileElementFileFromContents(path, contents)
                    #debug("        wrote contents")
                else:
                    warn("no catalogue directory tree files added for track #%s (titled [%s]) on the album [%s]: couldn't get the track's duration in seconds" % (numStr, title, albumPath))
                i += 1
        else:
            if info is None:
                warn("no catalogue directory tree files added for album [%s]: couldn't get track information" % albumPath)
            if perTrackSecs is None:
                warn("no catalogue directory tree files added for album [%s]: couldn't get track durations" % albumPath)

    def _fs_addFileForRealTrack(self, path, relPath):
        """
        Adds a file to our directory tree for the "real" track FLAC file with
        pathname 'path'. The track file's pathname in the file we're adding
        will be 'relPath'.
        """
        assert path is not None
        assert os.path.isabs(path)
        assert relPath is not None
        assert not os.path.isabs(relPath)
        #debug("---> in _fs_MetadataCatalogueBuilder._fs_addFileForRealTrack(%s, %s)" % (path, relPath))
        self._fs_writeRealFileDirectoryTreeFile(path, relPath)


class _fs_AlbumInformation(object):
    """
    Contains information about a single album that can be cached.
    """

    def __init__(self, albumFile, trackFilenames):
        """
        Initializes us with the pathname 'albumFile' of our album's album
        FLAC file and a list 'trackFilenames' of the base filenames of the
        FLAC track files for each of our album's tracks, in order by track
        number
        """
        assert albumFile
        assert trackFilenames is not None
        self._fs_albumFile = albumFile
        entries = []
        for name in trackFilenames:
            entries.append(Direntry(name))
        self._fs_direntries = entries

    def readdir(self):
        """
        Returns a list of Direntry (compatible) objects, one for each of our
        album's FLAC track files, in order by track number.
        """
        #assert result is not None
        return self._fs_direntries

    def albumFile(self):
        """
        Returns the pathname of our album's album FLAC file.
        """
        #assert result
        return self._fs_albumFile

class _fs_AlbumInformationCache(ut.ut_LeastRecentlyUsedCache):
    """
    The class of cache used in fs_AlbumAndTrackInformationCaches to map
    albums' pathnames to their information.
    """

    def __init__(self, trackMap, lowSize, highSize):
        """
        Initializes us with our low and high sizes, as well as 'trackMap',
        which maps the pathname of each track of each and every one of our
        albums to the pathname of the album containing the track.
        """
        assert trackMap is not None
        self._fs_trackMap = trackMap
        ut.ut_LeastRecentlyUsedCache.__init__(self, lowSize, highSize)

    def _onRemoval(self, key, value):
        # When removing an ambum from this cache also remove all of its
        # tracks from the track map.
        #
        # Note: 'value' is an instance of _fs_AlbumInformation.
        trackMap = self._fs_trackMap
        join = os.path.join
        for entry in value.readdir():
            trackPath = join(key, entry.name)
            del trackMap[trackPath]

class fs_AlbumAndTrackInformationCache(object):
    """
    A cache used by fs_FlacTrackFilesystems to cache readdir() and getattr()
    information about the most recently used albums and their tracks.
    """

    def __init__(self, lowSize, highSize):
        """
        Initializes us from our low and high sizes.

        Note: that the low and high sizes apply only to the number of albums
        whose information is kept in this cache: we will always contain
        information for all of our albums' tracks regardless of how many
        there are.

        See ut_LeastRecentlyUsedCache.__init__().
        """
        m = self._fs_trackPathToAlbumPath = {}
        self._fs_albumCache = _fs_AlbumInformationCache(m, lowSize, highSize)
            # maps the pathnames of album directories to an
            # _fs_AlbumInformation object containing the album's information

    def addAlbum(self, path, albumFile, trackFilenames):
        """
        Adds a mapping to this cache from the album directory pathname
        'path' to an _fs_AlbumInformation object that contains the album
        FLAC file pathname 'albumFile' and the track FLAC file base
        filenames in the list 'trackFilenames' (which are assumed to be
        in order by track number).
        """
        assert path
        assert albumFile
        assert trackFilenames is not None
        info = _fs_AlbumInformation(albumFile, trackFilenames)
        self._fs_albumCache.add(path, info)

        m = self._fs_trackPathToAlbumPath
        join = os.path.join
        for name in trackFilenames:
            trackPath = join(path, name)
            m[trackPath] = path

    def readdir(self, path, offset):
        """
        Returns a list of the Direntry objects for each of the track
        files in the album directory with pathname 'path' if we contain
        information about that album, and returns None otherwise.
        """
        result = None
        info = self._fs_albumCache.get(path)
        if info is not None:
            result = info.readdir()
        # 'result' may be None
        return result

    def originFile(self, path):
        """
        Returns the pathname of the file that is the origin file for the
        album directory or track file with pathname 'path' if we contain
        information about that album or track, and returns None otherwise.
        """
        result = None
        ac = self._fs_albumCache
        info = ac.get(path)
        if info is not None:
            # 'path' is an album directory pathname: we use the parent
            # directory of its album FLAC file as its origin file.
            result = os.path.dirname(info.albumFile())
        else:
            albumPath = self._fs_trackPathToAlbumPath.get(path)
            if albumPath is not None:
                info = ac.get(albumPath)
                if info is not None:
                    result = info.albumFile()
        # 'result' may be None
        return result

class fs_FlacTrackFilesystem(musicfs.fs_AbstractMusicFilesystem):
    """
    Represents filesystems that contain the result of merging the files
    under a 'realDir' directory (if any) and the FLAC files that represent
    the individual tracks of the albums represented by the FLAC and CUE files
    under a directory 'albumDir'.

# TODO: look for CUE files in the FLAC files themselves too ???!!!???
    A FLAC file under the 'albumDir' is considered to represent an album iff
    there is a file in the same directory with the same name as the FLAC file
    with an additional '.cue' extension appended to it. Such FLAC files are
    referred to here as 'album FLAC files'.

    An album flac file with pathname '$albumDir/some/dirs/name.flac' will
    generate files of the form '$mountDir/some/dirs/name/nn_xxx.flac', where
    $mountDir is the directory our filesystem is mounted on and each
    'nn_xxx.flac' is the per-track FLAC file for the 'nn'th track on the
    album. The 'nn' part is always 2 digits long and is padded with a
    leading zero if necessary. The 'xxx' part is built from the track's
    title and the artist's name after removing and translating various
    inconvenient characters.
    """

    def __init__(self, *args, **kw):
        musicfs.fs_AbstractMusicFilesystem.__init__(self, *args, **kw)
        #self._fs_trackExtractor = music.mu_FfmpegFlacAlbumTrackExtractor()
        self._fs_trackExtractor = music.mu_DefaultFlacAlbumTrackExtractor()
        self._fs_albumAndTrackCache = \
            fs_AlbumAndTrackInformationCache(_fs_lowAlbumCacheSize,
                                             _fs_highAlbumCacheSize)

    def fs_processOptions(self, opts):
        musicfs.fs_AbstractMusicFilesystem.fs_processOptions(self, opts)

        val = fscommon.fs_parseRequiredSuboption(opts, fs_albumDirOption)
        self._fs_albumDir = ut.ut_expandedAbsolutePathname(val)

    def _fs_readdir(self, path, offset):
        #debug("---> in fs_FlacTrackFilesystem._fs_readdir(%s, %s)" % (path, str(offset)))
        result = self._fs_albumAndTrackCache.readdir(path, offset)
        #debug("    result from album and track cache? %s" % str(result is not None))
        if result is None:
            result = musicfs.fs_AbstractMusicFilesystem. \
                _fs_readdir(self, path, offset)
        return result

    def fs_albumDirectory(self):
        """
        Returns the absolute pathname of the directory under which the
        FLAC and CUE files representing entire albums are located.
        """
        result = self._fs_albumDir
        assert result is not None
        assert os.path.isabs(result)
        return result


    def _fs_generateDirectoryEntryNames(self, path):
        assert path is not None
        #debug("---> in _fs_generateDirectoryEntryNames(%s)" % path)
        (albumFile, cueFile) = self. \
            _fs_existingAlbumAndCueFilePathnames(path)
        #debug("    album path = [%s], cue path = [%s]" % (albumFile, cueFile))
        if albumFile is not None and cueFile is not None:
            # The directory's contents are the filenames of the single-track
            # FLAC files for each of the tracks.
            #
            # Note: this will hide any existing directory under our album
            # directory whose pathname is 'albumFile' but without the .flac
            # extension.
            names = self._fs_allAlbumTrackFilenames(albumFile, cueFile)
            self._fs_albumAndTrackCache.addAlbum(path, albumFile, names)
            for f in names:
                yield f
        else:
            #debug("    path does NOT map to an album file")
            subdir = fscommon.fs_pathnameRelativeTo(self.fs_albumDirectory(),
                                                    path)
            #debug("    subdir = [%s]" % subdir)
            if os.path.isdir(subdir):
                #debug("    'subdir' is a directory")
                albumDirs = set()
                nonAlbumDirs = []
                for f in os.listdir(subdir):
                    # Only include subdirectories corresponding to album FLAC
                    # files and actual subdirectories (with the former
                    # possibly hiding the latter).
                    if music.mu_hasFlacFilename(f):
                        (base, ext) = os.path.splitext(f)
                        basePath = os.path.join(path, base)
                        (albumFile, cueFile) = self. \
                            _fs_existingAlbumAndCueFilePathnames(basePath)
                        if albumFile is not None and cueFile is not None:
                            albumDirs.add(base)
                    # This isn't an 'elif' because we could conceivably have
                    # a directory ending in '.flac' (which can't be an album
                    # FLAC file).
                    if os.path.isdir(os.path.join(subdir, f)):
                        nonAlbumDirs.append(f)  # actual subdirectory
                for f in albumDirs:
                    yield f
                for f in nonAlbumDirs:
                    if not f in albumDirs:
                        yield f

    def _fs_allAlbumTrackFilenames(self, albumFile, cueFile):
        """
        Returns a list of the (base) filenames of all of the tracks on the
        album represented by the FLAC album file with pathname 'albumFile'
        and its associated CUE file, which has pathname 'cueFile'.
        """
        result = []
        info = music.mu_allAlbumTrackInformation(albumFile, cueFile)
        if info is not None:
            for (num, title, artist) in info:
                f = self.fs_buildFilenameOfTrackNumber(num, title, artist)
                result.append(f)
        assert result is not None
        return result

    def _fs_generateFile(self, path, cachedPath, finalCachedPath):
        #debug("---> in fs_FlacTrackFilesystem._fs_generateFile(%s, %s, %s)" % (path, cachedPath, finalCachedPath))
        assert path is not None
        assert cachedPath is not None
        assert os.path.isabs(cachedPath)
        assert finalCachedPath is not None
        assert os.path.isabs(finalCachedPath)
        result = None
        doGenerate = True
        (parent, filename) = os.path.split(path)
        #debug("    parent dir = [%s], filename = [%s]" % (parent, filename))
        (grandparent, albumFilenameBase) = os.path.split(parent)
        #debug("    grandparent dir = [%s], album filename base = [%s]" % (grandparent, albumFilenameBase))
        if len(albumFilenameBase) > 0 and music.mu_hasFlacFilename(filename):
            #debug("    '%s' is likely the pathname of an album's track" % path)
            relPath = os.path.join(grandparent, albumFilenameBase)
            #debug("    relative path for album file = [%s]" % relPath)
            (albumFile, cueFile) = self. \
                _fs_existingAlbumAndCueFilePathnames(relPath)
            #debug("    album file = [%s], cue file = [%s]" % (albumFile, cueFile))
            if albumFile is not None and cueFile is not None:
                #debug("    it IS an album file: generating it ...")
                doGenerate = False
                result = self._fs_generateTrackFile(albumFile, cueFile,
                                    filename, cachedPath, finalCachedPath)
                if result is None:
# TODO: is there a better class of exception to throw here ???!!!!???
                    raise ValueError("failed to start generating the "
                        "cached FLAC track file '%s' asynchronously" %
                        finalCachedPath)
        if doGenerate:
            # Check whether 'path' corresponds to a directory we generate
            # to "represent" an album FLAC file.
            #debug("    check whether '%s' corresponds to a directory we generate to represent an album FLAC file" % path)
            (albumFile, cueFile) = self. \
                _fs_existingAlbumAndCueFilePathnames(path)
            #debug("        album file = [%s], cue file = [%s]" % (albumFile, cueFile))
            if albumFile is not None and cueFile is not None:
                # 'path' is a directory generated for an album FLAC file.
                doGenerate = False
                #debug("        the path was indeed generated for an album FLAC file: creating the corresponding cache directory '%s'" % cachedPath)
                self._fs_createGeneratedDirectory(cachedPath)
                #debug("        created dir [%s]" % cachedPath)
        if doGenerate:
            # See if we need to generate a "plain" directory instead.
            f = fscommon.fs_pathnameRelativeTo(self.fs_albumDirectory(),
                                               path)
            #debug("    see if we need to generate a 'plain' directory '%s'" % f)
            if os.path.isdir(f):
                #debug("        Yes. creating the directory '%s'" % cachedPath)
                doGenerate = False
                self._fs_createGeneratedDirectory(cachedPath)
        #debug("    result = %s" % str(result))
        # 'result' may be None
        return result

    def _fs_generatedFileOriginFilePathname(self, path):
        assert path is not None
        #debug("---> in fs_FlacTrackFilesystem._fs_generatedFileOriginFilePathname(%s)" % path)
        result = self._fs_albumAndTrackCache.originFile(path)
        #debug("    origin file pathname from album and track cache = [%s]" % result)
        if result is None:
            if music.mu_hasFlacFilename(path):
                (albumDir, trackFilename) = os.path.split(path)
                if len(albumDir) > 0:
                    (albumFile, cueFile) = self. \
                        _fs_existingAlbumAndCueFilePathnames(albumDir)
                    if albumFile is not None and cueFile is not None and \
                       self._fs_hasTrackFileNamed(trackFilename,
                                                  albumFile, cueFile):
                        #debug("    using album FLAC file [%s] as the origin file for a track file" % albumFile)
                        result = albumFile
            else:
                (albumFile, cueFile) = self. \
                    _fs_existingAlbumAndCueFilePathnames(path)
                if albumFile is not None and cueFile is not None:
                    # Note: we don't use the album FLAC file itself as the
                    # origin file because file modes for files don't
                    # necessarily work well for directories (e.g. executable
                    # bits).
                    result = os.path.dirname(albumFile)
                    #debug("    using the parent directory [%s] as the origin file for the directory corresponding to the album FLAC file [%s]" % (result, albumFile))
                else:
                    d = self.fs_albumDirectory()
                    d = fscommon.fs_pathnameRelativeTo(d, path)
                    if os.path.isdir(d):
                        #debug("    origin file is 'plain' directory [%s]" % d)
                        result = d
        # 'result' may be None
        #debug("    result = %s" % str(result))
        return result

    def _fs_hasTrackFileNamed(self, trackFilename, albumFile, cueFile):
        """
        Returns True iff the album represented by the album FLAC file with
        pathname 'albumFile' and the CUE file with pathname 'cueFile' has a
        track that would be represented in this filesystem by a file whose
        basename is 'trackFilename'.

        Note: this method does NOT generate any files.
        """
        #debug("---> in _fs_hasTrackFileNamed(%s, %s, %s,)" % (trackFilename, albumFile, cueFile))
        assert trackFilename is not None
        assert albumFile is not None
        assert ut.ut_isExistingRegularFile(albumFile)
        assert cueFile is not None
        assert ut.ut_isExistingRegularFile(cueFile)
        result = False
        (num, title, artist) = self._fs_parseTrackFilename(albumFile,
                                                    cueFile, trackFilename)
        if num > 0 and title is not None and artist is not None:
            fname = self.fs_buildFilenameOfTrackNumber(num, title, artist)
            #debug("    fname = [%s], track filename = [%s]" % (fname, trackFilename))
            result = (fname == trackFilename)
        return result

    def _fs_generateTrackFile(self, albumFile, cueFile, trackFilename, path,
                              finalPath):
        """
        Asynchronously generates a single-track FLAC file with absolute
        pathname 'path' that represents the track with base filename
        'trackFilename' in the album represented by the album FLAC file with
        pathname 'albumFile' and the associated CUE file with pathname
        'cueFile', then - iff it's fully successful - it renames the file
        with pathname 'path' to have the pathname 'finalPath'.

        Both 'albumFile' and 'cueFile' are assumed to exist (though they may
        be links to the actual files).

        Returns a readable file descriptor from which can be read the file's
        contents as they're generated, or returns None if asynchronous file
        generation couldn't be started.
        """
        #debug("---> in _fs_generateTrackFile(%s, %s, %s, %s)" % (albumFile, cueFile, trackFilename, path))
        assert albumFile is not None
        #assert ut.ut_isExistingRegularFile(albumFile)
        assert cueFile is not None
        #assert ut.ut_isExistingRegularFile(cueFile)
        assert trackFilename is not None
        assert trackFilename == os.path.basename(trackFilename)
        assert path is not None
        assert os.path.isabs(path)
        assert finalPath is not None
        assert os.path.isabs(finalPath)
        result = None
        (num, title, artist) = self._fs_parseTrackFilename(albumFile,
                                                    cueFile, trackFilename)
        fname = self.fs_buildFilenameOfTrackNumber(num, title, artist)
        if fname == trackFilename:
            #debug("    asynchronously generating FLAC track file ...")
            cmd = self._fs_trackExtractor.mu_createShellCommand(albumFile,
                                                cueFile, num, title, artist)
            (result, wfd) = os.pipe()
            #debug("    cmd = '%s', result (fd) = %i" % (cmd, result))
# TODO: we need to handle errors that occur in executing the command !!!
# - even (esp.) when it's the first/earlier command in a pipeline
            proc = mergedfs.fs_GenerateFileFromCommandDaemonProcess(cmd,
                                                result, wfd, path, finalPath)
        #debug("    did track file generation start? %s" % str(result is not None))
        # 'result' may be None
        return result

    def _fs_createCatalogueSummaryMetadataFileBuilder(self, baseDir):
        assert baseDir is not None
        assert os.path.isabs(baseDir)
        result = _fs_MetadataCatalogueBuilder(self, baseDir)
        assert result is not None
        return result

    def _fs_parseTrackFilename(self, albumFile, cueFile, trackFilename):
        """
        Returns a 3-tuple containing the track number, title and artist (in
        that order) of the track of the album represented by the album FLAC
        file with pathname 'albumFile' and the CUE file with pathname
        'cueFile' that would be represented by a file with basename
        'trackFilename' in this filesystem. There is no such track iff the
        first item in 'result' is 0.
        """
        assert trackFilename is not None
        assert albumFile is not None
        assert ut.ut_isExistingRegularFile(albumFile)
        assert cueFile is not None
        assert ut.ut_isExistingRegularFile(cueFile)
        trackNum = self._fs_trackNumberFromFilename(trackFilename)
        if trackNum > 0:
            (title, artist) = self. \
                _fs_trackTitleAndArtist(trackNum, albumFile, cueFile)
            #debug("    title = [%s], artist = [%s]" % (title, artist))
        else:
            assert trackNum == 0
            title = None
            artist = None
        result = (trackNum, title, artist)
        assert len(result) == 3
        assert result[0] >= 0
        assert (result[1] is None) or (result[2] is not None)
            # title is not None implies artist is not None
        assert result[0] > 0 or (result[1] is None and result[2] is None)
        return result


    def _fs_existingAlbumAndCueFilePathnames(self, path):
        """
        Returns the pathnames of the album FLAC file and corresponding CUE
        file that correspond to the directory in this filesystem with
        pathname 'path', if such files exist and a regular files: otherwise
        the corresponding item in the pair will be None.

        This method assumes that 'path' is relative to our mount point
        (though it starts with a pathname separator).
        """
        #debug("---> in _fs_existingAlbumAndCueFilePathnames(%s)" % path)
        assert path is not None
        assert not music.mu_hasFlacFilename(path)
        cueFile = None
        albumFile = fscommon.fs_pathnameRelativeTo(self.fs_albumDirectory(),
                                                   path)
        #debug("    album path = [%s]" % albumFile)
        albumFile = music.mu_addFlacExtension(albumFile)
        #debug("    album path = [%s]" % albumFile)
        cueFile = self.fs_pathnameForCueFileForAlbum(albumFile)
        #debug("    cue path = [%s]" % cueFile)
        if not ut.ut_isExistingRegularFile(albumFile):
            #debug("        album path is NOT an existing regular file")
            albumFile = None
        if not ut.ut_isExistingRegularFile(cueFile):
            #debug("        cue path is NOT an existing regular file")
            cueFile = None
        result = (albumFile, cueFile)
        assert result is not None
        assert len(result) == 2
        assert result[0] is None or ut.ut_isExistingRegularFile(result[0])
        assert result[1] is None or ut.ut_isExistingRegularFile(result[1])
        # either or both items in the pair 'result' may be None
        #debug("    result = [%s]" % repr(result))
        return result

    def _fs_trackTitleAndArtist(self, trackNumber, albumFile, cueFile):
        """
        Returns the title and artist name for the 'trackNumber'th track of
        the album represented by the album FLAC file with pathname
        'albumFile' and CUE file with pathname 'cueFile'. Both components of
        the returned pair will be None if a proper value can't be determined
        for them.

        Note: if the title can be obtained but the artist can't then
        music.mu_unknownArtistName is returned as the artist.
        """
        #debug("---> in _fs_trackTitleAndArtist(%s, %s, %s)" % (str(trackNumber), albumFile, cueFile))
        assert trackNumber > 0
        assert albumFile is not None
        assert cueFile is not None
        (title, artist) = music.mu_trackTitleAndArtistFromCueFile(albumFile,
                                                        cueFile, trackNumber)
        #debug("    title = [%s], artist = [%s]" % (title, artist))
        if (title is not None) and (artist is None):
            artist = music.mu_unknownArtistName
            #debug("   artist set to '%s'" % artist)
        result = (title, artist)
        assert result is not None
        assert len(result) == 2
        assert (result[0] is None) or (result[1] is not None)
            # title is not None implies artist is not None
        return result

    def fs_buildFilenameOfTrackNumber(self, trackNumber, title, artist):
        """
        Returns the base filename for the per-track FLAC file for the
        'trackNumber'th track of an album, where the track's title is 'title'
        and its artist is 'artist'.
        """
        assert trackNumber > 0
        assert artist is not None
        assert title is not None
        numStr = music.mu_formatTrackNumber(trackNumber)
        result = "%s_%s_%s" % (numStr, title, artist)
        result = self._fs_simplifyFilename(result)
        result = music.mu_addFlacExtension(result)
        assert result is not None
        assert len(result) > 0
        return result

    def fs_pathnameForCueFileForAlbum(self, albumFilePathname):
        """
        Returns the pathname of the CUE file corresponding to the album
        FLAC file with pathname 'albumFilePathname'.
        """
        assert albumFilePathname is not None
        assert music.mu_hasFlacFilename(albumFilePathname)
        result = music.mu_addCueExtension(albumFilePathname)
        assert result is not None
        return result


    def fs_hasTargetMusicFileFilename(self, f):
        # Overrides version in fs_AbstractMusicFilesystem.
        assert f is not None
        return music.mu_hasFlacFilename(f)

    def _fs_originsMetadataFileContents(self, origPath):
        # Overrides version in fs_AbstractMusicFilesystem.
        #debug("---> in fs_FlacTrackFilesystem._fs_originsMetadataFileContents(%s)" % origPath)
        assert origPath is not None
        realPath = self.fs_realFilePathname(origPath)
        if realPath is not None:
            #debug("    realPath is not None [%s]" % realPath)
# TODO: add a tag for the real file's pathname (= realPath) ???
            # There's no origins information for a "real" file (yet).
            result = ""  # empty metadata file
        else:
            dir = os.path.dirname(origPath)
            #debug("    parent dir = [%s]" % dir)
            (albumFile, cueFile) = self. \
                _fs_existingAlbumAndCueFilePathnames(dir)
            #debug("    albumFile = [%s], cueFile = [%s]" % (albumFile, cueFile))
            lines = []
            if albumFile is not None:
                tag = musicfs.fs_containerOriginsTagName
                lines.append(mergedfs.fs_tagMetadataFileLine(tag, albumFile))
                #debug("    lines = [%s]" % ", ".join(lines))
            if cueFile is not None:
                tag = musicfs.fs_containerIndexOriginsTagName
                lines.append(mergedfs.fs_tagMetadataFileLine(tag, cueFile))
                #debug("    lines = [%s]" % ", ".join(lines))
            result = mergedfs.fs_linesToMetadataFileContents(lines)
        #debug("    result = [%s]" % result)
        # 'result' can be None
        return result

    def _fs_tagsMetadataFileContents(self, origPath):
        # Overrides version in fs_AbstractMusicFilesystem.
        #debug("---> in fs_FlacTrackFilesystem._fs_tagsMetadataFileContents(%s)" % origPath)
        assert origPath is not None
        result = {}
        realPath = self.fs_realFilePathname(origPath)
        if realPath is not None and music.mu_hasFlacFilename(realPath):
            #debug("    real path = [%s]" % realPath)
            result = music.mu_flacTagsMap(realPath)
            assert result is not None
        else:
            (d, fname) = os.path.split(origPath)
            #debug("    dirname = [%s], fname = '%s'" % (d, fname))
            (album, cue) = self._fs_existingAlbumAndCueFilePathnames(d)
            #debug("    album file = [%s]" % album)
            #debug("    cue file   = [%s]" % cue)
            trackNum = self._fs_trackNumberFromFilename(fname)
            #debug("    track number = %s" % str(trackNum))
            if album is not None and cue is not None and trackNum > 0:
                result = music.mu_flacAlbumTrackTagsMap(album, cue, trackNum)
        result = mergedfs.fs_tagsMapToMetadataFileContents(result)
        #debug("    result = [%s]" % result)
        # 'result' can be None
        return result

    def _fs_derivedMetadataFileContents(self, origPath):
        # Overrides version in fs_AbstractMusicFilesystem.
        #debug("---> in fs_FlacTrackFilesystem._fs_derivedMetadataFileContents(%s)" % origPath)
        assert origPath is not None
        realPath = self.fs_realFilePathname(origPath)
        if realPath is not None and music.mu_hasFlacFilename(realPath):
            #debug("    real path = [%s]" % realPath)
            result = self. \
                _fs_buildDerivedMetadataFileContentsFromFile(realPath)
            assert result is not None
        else:
            (d, fname) = os.path.split(origPath)
            #debug("    dirname = [%s], fname = '%s'" % (d, fname))
            (album, cue) = self._fs_existingAlbumAndCueFilePathnames(d)
            #debug("    album file = [%s]" % album)
            #debug("    cue file   = [%s]" % cue)
            trackNum = self._fs_trackNumberFromFilename(fname)
            #debug("    track number = %s" % str(trackNum))
            perTrackSecs = music. \
                mu_allFlacAlbumTracksDurationsInSeconds(album, cue)
            if album is not None and cue is not None and \
                trackNum > 0 and perTrackSecs is not None:
                secs = perTrackSecs[trackNum - 1]
                result = self. \
                    _fs_buildDerivedMetadataFileContentsFromData(secs)
        #debug("    result = [%s]" % result)
        # 'result' can be None
        return result


# Main method.

def main():
    """
    Main method.
    """
    # flactrackfs -o albums=PATH [real=PATH] cache=PATH mountpoint
    usage = """

A filesystem that contains the result of merging the files under a
directory 'realDir' (if any) and the FLAC files that represent the
individual tracks of the albums represented by the FLAC and CUE files
under the directory 'albumDir'. The per-track FLAC files are cached
under the directory 'cacheDir'.

""" + fscommon.fs_commonUsage
    fs = fs_FlacTrackFilesystem(version="%prog " + fscommon.fs_fuseVersion,
                                 usage = usage, dash_s_do = 'setsingle')
    mergedfs.fs_addNoMetadataOption(fs.parser)
    fs.parser.add_option(mountopt = fs_albumDirOption, metavar = "PATH",
        help = "look for FLAC and CUE files representing entire albums under PATH")
    fs.parser.add_option(mountopt = mergedfs.fs_realDirOption,
        metavar = "PATH",
        help = "look for 'real' per-track FLAC files under PATH")
    fs.parser.add_option(mountopt = mergedfs.fs_cacheDirOption,
        metavar = "PATH", help = "cache per-track FLAC files under PATH")
    fs.fs_start(usage)
