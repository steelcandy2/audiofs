# Contains common configuration information for the programs and modules
# in this directory and its subdirectories.
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

import audiofs.utilities as ut


# Constants.

# The file extensions for various types of music files.
flacExtension = "flac"
mp3Extension = "mp3"
oggExtension = "ogg"

# The file extensions for files that contain sets of music file ratings.
ratingsFileExtension = "ratings"
fullRatingsFileExtension = ut.ut_fullExtension(ratingsFileExtension)

# The default file extension for playlist files.
defaultPlaylistExtension = "m3u"
fullDefaultPlaylistExtension = ut.ut_fullExtension(defaultPlaylistExtension)

# The maximum rating a music file can have.
#
# Note: if we ever decide to make this user-configurable first be sure that
# ALL of the code can handle its changing: for example, be sure that it can
# handle ratings that were valid but are now too large.
maxRating = 10

# The default pathname of the file to which information to be discarded is
# to be written.
_defaultDiscardFile = "/dev/null"


# Configuration file pathnames.
_configFilename = "configuration.py"
_siteConfigDir = os.path.join("/etc", "audiofs")
_userConfigDir = ut.ut_expandedAbsolutePathname(os.path.join("~", ".audiofs"))
_siteConfigFilePathname = os.path.join(_siteConfigDir, _configFilename)
_userConfigFilePathname = os.path.join(_userConfigDir, _configFilename)
#_userConfigFilePathname = "~/src/other/music/etc/" + _configFilename

_mpdSelectedServerFilename = "selected-mpd-server.txt"
_mpdSelectedServerPathname = os.path.join(_userConfigDir,
                                          _mpdSelectedServerFilename)

# The separator between the host and port of an MPD server in the
# "selected MPD server" configuration file.
_mpdServerHostPortSeparator = ":"


# The valid lengths of an MPD server description (which is a list).
_defaultMpdServerDescriptionLength = 2
_radioMpdServerDescriptionLength = _defaultMpdServerDescriptionLength + 1

# The 0-based indices of the various pieces of information in an MPD server
# description (which is a list).
_mpdServerHostnameIndex = 0
_mpdServerPortNumberIndex = 1
_mpdServerRadioInfoIndex = 2

# Keys and default values for information specific to radio MPD servers.
_radioMpdServerMinTracksAheadKey = "minTracksAhead"
_radioMpdServerMaxTracksAheadKey = "maxTracksAhead"
_radioMpdServerTracksBehindKey = "tracksBehind"
_radioMpdServerRatingsBasenameKey = "ratingsBasename"
_radioMpdServerRatingToChancesConverterKey = "ratingToChancesConverter"
_radioMpdServerIncludedGenresKey = "includedGenres"
_radioMpdServerExcludedGenresKey = "excludedGenres"
_requiredRadioMpdServerMapKeys = [
    _radioMpdServerMinTracksAheadKey,
    _radioMpdServerMaxTracksAheadKey]
_radioMpdServerMapDefaults = {
    _radioMpdServerTracksBehindKey: 10,
    _radioMpdServerRatingsBasenameKey: None,
        # really use mainRatingsBasename
    _radioMpdServerRatingToChancesConverterKey: "good",
    _radioMpdServerIncludedGenresKey: [],
    _radioMpdServerExcludedGenresKey: []}
_radioMpdServerMapKeys = _requiredRadioMpdServerMapKeys[:]  # copy
_radioMpdServerMapKeys.extend(_radioMpdServerMapDefaults.keys())


# The names of configuration variables whose values can be set in site or
# user configuration files.
_requiredConfigVarNames = ["tempDir", "rootDir", "baseSubdir", "dataDirs",
    "realFilesSubdir", "allFilesSubdir", "mainFormat", "albumKind",
    "trackKind", "mainKind", "formatPathnameComponentIndex",
    "kindPathnameComponentIndex", "nonAudioFileExtensions",
    "nonAudioSubdirectories",
    "otherSubdir", "binSubdir", "metadataSubdir", "playlistsSubdir",
    "customPlaylistsSubdir", "generatedPlaylistsSubdir",
    "ratingsSubdir", "systemSubdir", "documentationSubdir", "searchSubdir",
    "sourceMetadataDir", "sourcePlaylistsDir", "sourceRatingsDir",
    "catalogueFilename", "searchableTagNames",
    "mainRatingsBasename", "allRatingsBasenames", "defaultRating",
    "defaultPlaylistSize", "commonMountOptionsList",
    "flactrackMountPoint", "flactrackFilename", "flactrackCacheDir",
    "flactrackAlbumsDir", "flactrackRealDir", "allCacheDirs",
    "musicsearchFilename", "allFilesystemFilenames",
    "flac2mp3MountPointToBitrateMap", "flac2oggMountPointToBitrateMap",
    "docAlbumsHtmlStartFmt", "docAlbumsHtmlEndFmt", "docAlbumsHtmlItemFmt",
    "docTracksHtmlStartFmt", "docTracksHtmlEndFmt", "docTracksHtmlItemFmt",
    "mpdServers", "defaultMpdServerId",
    "fusermountProgram", "mpcProgram", "mpdProgram",
    "cueprintProgram", "cuebreakpointsProgram",
    "flacProgram", "metaflacProgram", "lameProgram", "id3v2Program",
    "ffmpegProgram", "ffprobeProgram",
    "oggencProgram", "vorbiscommentProgram"]
_optionalConfigVarNames = ["logFilePathname", "doDebugLogging",
    "doMountFilesystems", "mp3Format", "flacFormat", "oggFormat",
    "flac2mp3Filename", "flac2mp3CacheDir", "flac2mp3FlacDir",
    "flac2mp3RealDir",
    "flac2oggFilename", "flac2oggCacheDir", "flac2oggFlacDir",
    "flac2oggRealDir",
    "allNonmusicFilesystemMountPoints", "niceCommandPrefix", "discardFile",
    "mpdDisplayInformationProgram", "mpdDisplayInformationProgramArguments"]

# The name of the field used in a conf_Configuration instance to determine
# whether the instance has finished being initialized or not.
_conf_isInitializedField = '_conf_isInitialized'


# Functions.

def _join(path1, *paths):
    """
    See os.path.join()
    """
    return os.path.join(path1, *paths)


# Classes.

class conf_Configuration(object):
    """
    Represents the common configuration for music-related programs and
    modules.

    Note: instances are read-only.

    See obtain().
    """

    def initialize(self):
        """
        Initializes this instance by setting the values of all of its fields.
        """
        self._setPropertiesFromConfigurationFiles()


    def findConfigurationFile(self, basename):
        """
        Finds the configuration file whose basename is 'basename' by first
        looking for it in the user configuration directory, then if it's not
        there looking for it in the site configuration directory.

        Returns the absolute pathname of the configuration file if it's found
        and None otherwise.
        """
        result = None
        for d in [_userConfigDir, _siteConfigDir]:
            assert os.path.isabs(d)
            p = os.path.join(d, basename)
            if os.path.isfile(p):
                result = p
                break  # for
        assert result is None or os.path.isabs(result)
        return result

    def userConfigurationDirectory(self):
        """
        Returns the pathname of the user configuration directory.

        See findConfigurationFile(), siteConfigurationDirectory().
        """
        result = _userConfigDir
        assert result is not None
        assert os.path.isabs(result)
        return result

    def siteConfigurationDirectory(self):
        """
        Returns the pathname of the site configuration directory.

        See findConfigurationFile(), userConfigurationDirectory().
        """
        result = _siteConfigDir
        assert result is not None
        assert os.path.isabs(result)
        return result


    def isNonemptySearchDirectory(self):
        """
        Returns True iff this configuration specifies that a non-empty music
        search directory should be created.
        """
        return bool(self.searchableTagNames)

    def defaultMpdServer(self):
        """
        Returns the (hostname, port) pair for the default MPD server.
        """
        #assert result is not None
        #assert len(result) == 2
        #assert result[0]
        #assert ut.ut_isInt(result[1])
        id = self.defaultMpdServerId
        return self.mpdServer(self.mpdServerDescription(id))

    def selectedMpdServer(self):
        """
        Returns the (hostname, port) pair for the MPD server that is
        currently selected. (If one hasn't been selected explicitly then the
        default server - as specified in the main configuration file - is
        used.)

        If an MPD server hasn't been explicitly selected yet, or if the
        information in the selected MPD server configuration file is invalid
        or inaccessible then the default MPD server's information is returned
        and - if possible - is set as that of the default server.
        """
        result = None
        lines = ut.ut_readFileLines(_mpdSelectedServerPathname)
        if lines:
            # Ignore lines other than the first.
            res = lines[0].split(_mpdServerHostPortSeparator)
            if len(res) == 2:  # there's both a host and a port
                if res[0] and ut.ut_isInt(res[1]):
                    port = int(res[1])
                    if port >= 0:
                        # The values of the host and port are valid.
                        result = (res[0], port)
        if result is None:
            # Either no server's been selected or the information about it is
            # inaccessible or invalid.
            result = self.defaultMpdServer()
            try:
                self.setSelectedMpdServer(result[0], result[1])
            except IOError:
                pass  # our attempt failed, which is OK
        assert result is not None
        assert len(result) == 2
        assert result[0]
        assert ut.ut_isInt(result[1])
        return result

    def setSelectedMpdServer(self, host, port):
        """
        Sets the hostname and port of the selected MPD server to 'host' and
        'port', respectively, raising an IOError if we fail to set it.
        """
        #print("---> in conf_Configuration.setSelectedMpdServer(%s, %s)" % (host, str(port)))
        line = "%s%s%s" % (host, _mpdServerHostPortSeparator, str(port))
        #print("    pathname = [%s], line = [%s]" % (_mpdSelectedServerPathname, line))
        try:
            ut.ut_writeFileLines(_mpdSelectedServerPathname, [line])
        except:
            #print("    writing the selected server info failed")
            raise IOError("Failed to set the selected MPD server host and " +
                "port to '%s' and '%s', respectively" % (host, str(port)))


    def mpdServerDescription(self, serverId):
        """
        Returns a description of the MPD server whose ID is 'serverId', or
        returns None if there isn't a server with that ID.

        Note: the description is intentionally opaque: it is intended to be
        passed as an argument to some of our other methods.
        """
        assert serverId is not None
        try:
            result = self.mpdServers[serverId]
        except:
            result = None
        # 'result' may be None
        return result

    def smartMatchMpdServerIds(self, k):
        """
        Smart matches k against all of our MPD servers' IDs, returning a
        list of the matching (id, desc) pairs (where 'id' is a matching
        server ID and 'desc' is the description of the corresponding MPD
        server.)

        See utilities.ut_smartMatchKeys().
        """
        #assert result is not None
        return ut.ut_smartMatchKeys(k, self.mpdServers)

    def allMpdServerIds(self):
        """
        Returns a list of the server IDs of all of the MPD server specified
        in this configuration object. The returned list will have been sorted
        using the default sort order for strings.

        See allMpdServerDescriptions().
        """
        result = self.mpdServers.keys()
        result.sort()
        assert result is not None
        return result

    def allMpdServerDescriptions(self):
        """
        Returns a list of the descriptions of all of the MPD servers
        specified in this configuration object.

        The order in which the servers' descriptions appear in the returned
        list is undefined and not necessarily always the same.

        See mpdServerDescription().
        See allMpdServerIds().
        """
        result = self.mpdServers.values()
        assert result is not None
        assert len(result) == len(self.mpdServers)
        return result


    def mpdServer(self, desc):
        """
        Returns the (hostname, port) pair for the MPD server described by
        'desc'.

        See mpdServerDescription().
        """
        assert desc is not None
        result = (desc[_mpdServerHostnameIndex],
                  desc[_mpdServerPortNumberIndex])
        assert result is not None
        assert len(result) == 2
        assert result[0]
        assert ut.ut_isInt(result[1])
        return result

    def mpdServerWithId(self, serverId):
        """
        Returns the (hostname, port) pair for the MPD server with server ID
        'serverId', or returns None if there's no MPD server with that ID.
        """
        assert serverId is not None
        result = self.mpdServerDescription(serverId)
        if result is not None:
            result = self.mpdServer(result)
        # 'result' may be None
        assert result is None or len(result) == 2
        assert result is None or result[0]
        assert result is None or ut.ut_isInt(result[1])
        return result

    def isLocalMpdServer(self, desc):
        """
        Returns True iff the MPD server described by 'desc' is running (or
        will run) on the host that this method is called on.

        See mpdServerDescription().
        See utilities.ut_isLocalhost()
        """
        (host, port) = self.mpdServer(desc)
        return ut.ut_isLocalhost(host)


    def isRadioMpdServer(self, desc):
        """
        Returns True iff the MPD server described by 'desc' is a radio MPD
        server.

        See mpdServerDescription().
        """
        assert desc is not None
        return (len(desc) == _radioMpdServerDescriptionLength)

    def radioMinimumTracksBehind(self, desc):
        """
        Returns the minimum number of tracks before the current one that the
        radio MPD server described by 'desc' should keep.
        """
        assert desc is not None
        assert self.isRadioMpdServer(desc)
        key = _radioMpdServerTracksBehindKey
        result = self._radioMpdServerInformation(desc, key)
        assert result >= 0
        return result

    def radioMinimumTracksAhead(self, desc):
        """
        Returns the minimum number of tracks that the radio MPD server
        described by 'desc' should ensure exist after the current track.
        """
        assert desc is not None
        assert self.isRadioMpdServer(desc)
        key = _radioMpdServerMinTracksAheadKey
        result = self._radioMpdServerInformation(desc, key)
        assert result >= 0
        return result

    def radioMaximumTracksAhead(self, desc):
        """
        Returns the maximum number of tracks that the radio MPD server
        described by 'desc' should ensure exist after the current track.
        """
        assert desc is not None
        assert self.isRadioMpdServer(desc)
        key = _radioMpdServerMaxTracksAheadKey
        result = self._radioMpdServerInformation(desc, key)
        assert result >= 0
        #assert result >= self.radioMinimumTracksAhead(desc)
        return result

    def radioRatingsBasename(self, desc):
        """
        Returns the basename of the ratings to use in selecting tracks to be
        added to the radio MPD server described by 'desc'.
        """
        assert desc is not None
        assert self.isRadioMpdServer(desc)
        key = _radioMpdServerRatingsBasenameKey
        result = self._radioMpdServerInformation(desc, key)
        assert result
        return result

    def radioRatingToChancesConverter(self, desc):
        """
        Returns the name of the rating-to-chances method to use in
        selecting tracks to be added to the radio MPD server described by
        'desc'.
        """
        assert desc is not None
        assert self.isRadioMpdServer(desc)
        key = _radioMpdServerRatingToChancesConverterKey
        result = self._radioMpdServerInformation(desc, key)
        assert result
        #assert musicfs.fs_ratingToChancesConverter(result) is not None
        return result

    def radioIncludedGenres(self, desc):
        """
        Returns a (possibly empty) list of strings, each of which names a
        genre to include in the playlist of the radio MPD server described
        by 'desc'.

        Note: if the list is empty then all genres are to be included.
        """
        assert desc is not None
        assert self.isRadioMpdServer(desc)
        key = _radioMpdServerIncludedGenresKey
        result = self._radioMpdServerInformation(desc, key)
        assert result is not None
        return result

    def radioExcludedGenres(self, desc):
        """
        Returns a (possibly empty) list of strings, each of which names a
        genre to exclude from the playlist of the radio MPD server described
        by 'desc'.
        """
        assert desc is not None
        assert self.isRadioMpdServer(desc)
        key = _radioMpdServerExcludedGenresKey
        result = self._radioMpdServerInformation(desc, key)
        assert result is not None
        return result

    def _radioMpdServerInformation(self, desc, key):
        """
        Returns the piece of radio MPD server-specific information
        corresponding to 'key' that is part of the MPD server description
        'desc'.

        See mpdServerDescription().
        """
        assert desc is not None
        assert self.isRadioMpdServer(desc)
        assert key in _radioMpdServerMapKeys
        info = desc[_mpdServerRadioInfoIndex]
        result = info[key]
        # 'result' may be None
        return result


    def _setPropertiesFromConfigurationFiles(self):
        """
        Sets properties on this configuration object from the values of the
        variables set in the user and site configuration files.
        """
        m = self._buildConfigurationMap()
        missingRequiredVarNames = []
        for name in _requiredConfigVarNames:
            try:
                #print("---> calling setattr(%s, %s)" % (name, m[name]))
                setattr(self, name, m[name])
            except KeyError:
                missingRequiredVarNames.append(name)
        for name in _optionalConfigVarNames:
            try:
                setattr(self, name, m[name])
            except KeyError:
                #print("---> optional config var '%s' not specified" % name)
                pass
        if missingRequiredVarNames:
            raise AttributeError("The following required configuration "
                "variables were not set in the site or user configuration "
                "files: %s" % ", ".join(missingRequiredVarNames))

    def _buildConfigurationMap(self):
        """
        Builds and returns a map/dictionary containing configuration
        information. The information is obtained from the site and user
        configuration files.
        """
        #print("---> in _buildConfigurationMap()")
        result = self._buildInitialConfigurationMap()
        #print("_userConfigFilePathname = [%s]" % _userConfigFilePathname)
        self._updateMapFromConfigurationFile(_siteConfigFilePathname, result)
        self._updateMapFromConfigurationFile(_userConfigFilePathname, result)
        assert result is not None
        return result

    def _buildInitialConfigurationMap(self):
        """
        Builds and returns the map/dictionary that contains the initial
        configuration information, before any of the configuration files are
        processed.
        """
        nonAudioExts = [defaultPlaylistExtension, ratingsFileExtension]
        nonAudioSubdirs = []
        result = {
            "_join": _join,
            "nonAudioFileExtensions": nonAudioExts,
            "nonAudioSubdirectories": nonAudioSubdirs,

            # Set the default values of optional variables here.
            "mp3Format": mp3Extension,
            "flacFormat": flacExtension,
            "oggFormat": oggExtension,
            "doMountFilesystems": True,
            "doDebugLogging": False,
            "logFilePathname": None,
            "mpdDisplayInformationProgram": None,
            "mpdDisplayInformationProgramArguments": None,
            "niceCommandPrefix": "",
            "discardFile": _defaultDiscardFile
        }
        assert result is not None
        return result

    def _updateMapFromConfigurationFile(self, path, m):
        """
        Updates the map 'm' by executing the configuration file with pathname
        'path', if it exists.

        Raises a SyntaxError iff there's one or more syntax errors in one or
        more of the configuration files.
        """
        #print("---> in _updateMapFromConfigurationFile(%s, %s)" % (path, ut.ut_prettyShortMap(m)))
        assert path is not None
        assert m is not None
        p = os.path.expanduser(path)
        #print("    p = [%s]" % p)
        try:
            ut.ut_updateMapByExecutingFile(p, m)
        except IOError:
            pass  # just don't update the map if there's no config file
        #print("    done: m = %s" % ut.ut_prettyShortMap(m))

    def defineCalculatedVariables(self):
        """
        Defines configuration variables whose values are calculated from
        the ones defined in the configuration files.
        """
        self.baseDir = _join(self.rootDir, self.baseSubdir)

        # The subdirectory that contains files in the file format from which
        # ones in other formats are generated, and of the kind that other
        # kinds only represent a part of.
        if self.formatPathnameComponentIndex == 0:
            sd = _join(self.mainFormat, self.mainKind)
        else:
            sd = _join(self.mainKind, self.mainFormat)
        self.mainKindAndFormatSubdir = sd

        # Build the list of all music filesystem mount points.
        allPoints = [self.flactrackMountPoint]
        allPoints.extend(self.flac2mp3MountPointToBitrateMap)
        allPoints.extend(self.flac2oggMountPointToBitrateMap)
        self.allMusicFilesystemMountPoints = allPoints

        self.otherDir = _join(self.rootDir, self.otherSubdir)
        self.realFilesDir = _join(self.rootDir, self.realFilesSubdir)
        self.binDir = _join(self.otherDir, self.binSubdir)
        self.systemDir = _join(self.otherDir, self.systemSubdir)
        self.documentationDir = _join(self.otherDir,
                                      self.documentationSubdir)
        self.metadataDir = _join(self.otherDir, self.metadataSubdir)
        self.playlistsDir = _join(self.otherDir, self.playlistsSubdir)
        self.customPlaylistsDir = _join(self.playlistsDir,
                                        self.customPlaylistsSubdir)
        self.generatedPlaylistsDir = _join(self.playlistsDir,
                                           self.generatedPlaylistsSubdir)
        self.ratingsDir = _join(self.otherDir, self.ratingsSubdir)
        self.searchDir = _join(self.otherDir, self.searchSubdir)
        self.cataloguePathname = _join(self.metadataDir,
                                       self.catalogueFilename)

        # Build the list of all (music and non-music) filesystem mount
        # points.
        allPoints = allPoints[:]
        if hasattr(self, "allNonmusicFilesystemMountPoints"):
            allPoints.extend(self.allNonmusicFilesystemMountPoints)
        if self.isNonemptySearchDirectory():
            allPoints.append(self.searchDir)
        self.allFilesystemMountPoints = allPoints
        self.commonMountOptions = ",".join(self.commonMountOptionsList)

        # The indices relative to rootDir, not baseDir.
        sep = os.sep
        bsdir = self.baseSubdir.strip(sep)
        if bsdir:
            adj = bsdir.count(sep) + 1
        else:
            adj = 0
        self.rootKindPathnameComponentIndex = \
            self.kindPathnameComponentIndex + adj
        self.rootFormatPathnameComponentIndex = \
            self.formatPathnameComponentIndex + adj

    def __init__(self):
        initVar = _conf_isInitializedField
        self.__dict__[initVar] = False
        try:
            self.initialize()
            self.defineCalculatedVariables()
        finally:
            self.__dict__[initVar] = True
        self.checkConfiguration()
            # we intentionally do this AFTER we can't be modified

    def __setattr__(self, name, value):
        isInit = getattr(self, _conf_isInitializedField)
        if isInit:
            raise AttributeError("can't set configuration information: " +
                                 "it's read-only")
        else:
            self.__dict__[name] = value

    def __delattr__(self, name):
        raise AttributeError("can't delete configuration information: "
                             "it's read-only")


    def checkConfiguration(self):
        """
        Performs various checks to help ensure that this configuration is a
        valid one.
        """
        self._check(ut.ut_hasPathnamePrefix(self.baseDir, self.rootDir),
            "the baseDir '%s' MUST be a subdirectory of the root "
            "directory '%s', but it isn't" % (self.baseDir, self.rootDir))

        self._check(self.flac2mp3MountPointToBitrateMap is not None,
            "the flac2mp3MountPointToBitrateMap cannot be None: it must be "
            "a (possibly empty) map/dictionary")
        self._check(self.flac2oggMountPointToBitrateMap is not None,
            "the flac2oggMountPointToBitrateMap cannot be None: it must be "
            "a (possibly empty) map/dictionary")

        self._checkIsNonnegativeInt(self.defaultRating,
            "the defaultRating '%s' must be a non-negative integer, but it "
            "isn't" % self.defaultRating)
        self._checkIsInt(self.defaultPlaylistSize, "the defaultPlaylistSize "
                         "'%s' must be a positive integer, but it isn't" %
                         self.defaultPlaylistSize)
        self._check(self.defaultPlaylistSize > 0,
            "the defaultPlaylistSize must be greater than zero")

        rootDir = self.rootDir
        fmt = "the %s '%s' isn't allowed to be under the root " + \
              "directory '" + rootDir + "'"
        self._checkNotUnder(rootDir, self.sourceMetadataDir,
                    fmt % ("sourceMetadataDir", self.sourceMetadataDir))
        self._checkNotUnder(rootDir, self.sourcePlaylistsDir,
                    fmt % ("sourcePlaylistsDir", self.sourcePlaylistsDir))
        self._checkNotUnder(rootDir, self.sourceRatingsDir,
                    fmt % ("sourceRatingsDir", self.sourceRatingsDir))
        for d in self.dataDirs:
            self._checkNotUnder(rootDir, d, "data directories aren't "
                "allowed to be under the root directory '%s', but the "
                "data directory '%s' is" % (rootDir, d))
        for d in self.allCacheDirs:
            self._checkNotUnder(rootDir, d, "cache directories aren't "
                "allowed to be under the root directory '%s', but the "
                "cache directory '%s' is" % (rootDir, d))

        ki = self.kindPathnameComponentIndex
        fi = self.formatPathnameComponentIndex
        self._check((ki == 0 and fi == 1) or (ki == 1 and fi == 0),
            "either the kindPathnameComponentIndex must be 0 and the "
            "formatPathnameComponentIndex must be 1 or vice versa.")

        p = "flac2mp3MountPointToBitrateMap"
        if self.flac2mp3MountPointToBitrateMap:
            self._checkPropertyExistsForNonemptyMap("flac2mp3Filename", p)
            self._checkPropertyExistsForNonemptyMap("flac2mp3CacheDir", p)
            self._checkPropertyExistsForNonemptyMap("flac2mp3FlacDir", p)
            # property "flac2mp3RealDir" is optional

        p = "flac2oggMountPointToBitrateMap"
        if self.flac2oggMountPointToBitrateMap:
            self._checkPropertyExistsForNonemptyMap("flac2oggFilename", p)
            self._checkPropertyExistsForNonemptyMap("flac2oggCacheDir", p)
            self._checkPropertyExistsForNonemptyMap("flac2oggFlacDir", p)
            # property "flac2oggRealDir" is optional

        self._checkMpdServersMap(self.mpdServers, "mpdServers")
        self._check(self.defaultMpdServerId in self.mpdServers,
            "the value of the 'defaultMpdServerId' property is '%s', "
            "which is not a key in the 'mpdServers' map" %
            self.defaultMpdServerId)

    def _checkMpdServersMap(self, m, propertyName):
        """
        Checks that the value 'm' of the configuration property named
        'propertyName' on this configuration object is a valid MPD server
        map, raising an exception if it isn't. It also adds missing radio
        server information (using the default values).

        Note: this method doesn't check that the configuration property
        exists on this configuration object: that is assumed to have been
        done already.
        """
        assert propertyName
        self._check(m is not None, "The '%s' MPD servers map cannot be "
            "None: it must be a non-empty map/dictionary" % propertyName)
        h2p = {}  # maps hostnames to lists of port numbers
        minLen = _defaultMpdServerDescriptionLength
        maxLen = _radioMpdServerDescriptionLength
        for (id, desc) in m.items():
            try:
                n = len(desc)
            except TypeError:
                self._check(False, "in the MPD servers map '%s' the ID '%s' "
                    "must map to a list, but doesn't" % (propertyName, id))

            self._check(minLen <= n <= maxLen, "in the MPD servers "
                "map '%s' the ID '%s' must map to a list of length "
                "%i or %i, but it maps to a list of length %i" %
                (propertyName, id, minLen, maxLen, n))
            host = desc[_mpdServerHostnameIndex]
            port = desc[_mpdServerPortNumberIndex]
            self._checkHostname(host, "the hostname of the MPD "
                "server with ID '%s' in the MPD servers map '%s'" %
                (id, propertyName))
            self._checkPortNumber(port, "the port number of the MPD "
                "server with ID '%s' in the MPD servers map '%s'" %
                (id, propertyName))
            if host in h2p:
                val = h2p[host]
                if port in val:
                    self._check(False, "the MPD servers map '%s' "
                        "contains more than one item describing the "
                        "server with hostname '%s' and port number "
                        "'%i': the item for server ID '%s' is the "
                        "second" % (propertyName, host, port, id))
                else:
                    val.append(port)
            else:
                h2p[host] = [port]
            if self.isRadioMpdServer(desc):
                self._checkAndExpandRadioMpdServerDescription(id,
                    desc[_mpdServerRadioInfoIndex], propertyName)

    def _checkAndExpandRadioMpdServerDescription(self, id, m,
                                                 propertyName):
        """
        Checks that the map 'm' that contains radio server-specific
        information about an MPD server is valid, raising an exception if it
        isn't. It also adds items to 'm' (mapping to default values) for each
        item in it that isn't explicitly specified.

        'm' describes the MPD radio server with ID 'id' in the MPD servers
        map that is the value of the property named 'propertyName' in this
        configuration object.
        """
        assert id is not None
        assert m is not None
        assert propertyName

        msg1 = "the radio server information map for the MPD server with " \
            "ID '%s' in the MPD servers map '%s'" % (id, propertyName)
        nonegFmt = "the '%s' in " + msg1 + " must be non-negative, but " \
            "it is '%s'"
        notEmptyFmt = "the '%s' in " + msg1 + " cannot be empty (or None)"

        defs = _radioMpdServerMapDefaults
        reqKeys = _requiredRadioMpdServerMapKeys

        for k in reqKeys:
            self._check(k in m, "%s is missing the required '%s' "
                        "item" % (msg1, k))

        k = _radioMpdServerMinTracksAheadKey
        assert k in reqKeys
        v = m[k]
        self._checkIsNonnegativeInt(v, nonegFmt % (k, v))

        k1 = _radioMpdServerMaxTracksAheadKey
        assert k1 in reqKeys
        v1 = m[k1]
        self._checkIsNonnegativeInt(v1, nonegFmt % (k1, v1))
        self._check(v1 >= v, "the '%s' in %s must be greater than or "
            "equal to the '%s' %i, but it is only %i" % (k1, msg1, k, v, v1))

        k = _radioMpdServerTracksBehindKey
        assert k in defs
        if k in m:
            v = m[k]
            self._checkIsNonnegativeInt(v, nonegFmt % (k, v))
        else:
            m[k] = defs[k]

        k = _radioMpdServerRatingsBasenameKey
        assert k in defs
        if k in m:
            v = m[k]
            self._check(v, notEmptyFmt % k)
        else:
            m[k] = self.mainRatingsBasename

        k = _radioMpdServerRatingToChancesConverterKey
        assert k in defs
        if k in m:
            # NOTE: since musicfs imports us already, any attempt to import
            # musicfs here results in a circular dependency at runtime.
            #f = musicfs.fs_ratingToChancesConverter(v)
            #self._check(f is not None, "the '%s' in %s is '%s', which "
            #    "isn't a valid rating-to-chances conversion method name" %
            #    (k, msg1, v))
            self._check(v, notEmptyFmt % k)
        else:
            m[k] = defs[k]

        for k in [_radioMpdServerIncludedGenresKey,
                  _radioMpdServerExcludedGenresKey]:
            assert k in defs
            if k in m:
                pass
            else:
                m[k] = defs[k]
        assert len(m) == len(_radioMpdServerMapKeys)
            # or else we haven't checked every radio server info key
            # (since we've added to 'm' all keys not explicitly specified)


    def _checkPropertyExistsForNonemptyMap(self, propertyName,
                                           mapPropertyName):
        """
        Checks that the configuration property named 'propertyName' exists
        on this configuration object, raising an exception if it doesn't: the
        property is required to exist because a map-valued configuration
        property named 'mapPropertyName' exists on this configuration object
        and its (map) value is non-empty.

        Note: this method doesn't check whether a configuration property
        named 'mapPropertyName' actually exists on this configuration object,
        or that its value is a non-empty map.
        """
        assert propertyName is not None
        assert mapPropertyName is not None
        if not hasattr(self, propertyName):
            msg = "since the '%s' configuration property has been " \
                "specified and is non-empty the '%s' configuration " \
                "property must also be specified." % \
                (mapPropertyName, propertyName)
            raise ValueError(msg)

    def _checkPropertyExists(self, propertyName, propertyName2):
        """
        Checks that the configuration property named 'propertyName' exists
        on this configuration object, raising an exception if it doesn't: the
        property is required to exist because a configuration property named
        'propertyName2' exists on this configuration object.

        Note: this method doesn't check whether a configuration property
        named 'propertyName2' actually exists on this configuration object.
        """
        assert propertyName is not None
        assert propertyName2 is not None
        if not hasattr(self, propertyName):
            msg = "since the '%s' configuration property has been " \
                "specified the '%s' configuration property must also be " \
                "specified." % (propertyName2, propertyName)
            raise ValueError(msg)

    def _checkHostname(self, value, desc):
        """
        Checks that the value 'value' described by 'desc' is a valid hostname,
        raising an exception if it isn't.
        """
        # Currently we only check that it's non-empty.
        self._check(value, "%s cannot be empty (or None)" % desc)

    def _checkPortNumber(self, value, desc):
        """
        Checks that the value 'value' described by 'desc' is a valid port
        number, raising an exception if it isn't.
        """
        msg = "%s must be a non-negative integer" % desc
        self._checkIsNonnegativeInt(value, msg)

    def _checkIsNonnegativeInt(self, value, msg):
        """
        Checks that 'value' can be converted to a non-negative int, raising
        an exception with message 'msg' if it can't.
        """
        self._checkIsInt(value, msg)
        self._check(int(value) >= 0, msg)

    def _checkIsInt(self, value, msg):
        """
        Checks that 'value' can be converted to an int, raising an exception
        with message 'msg' if it can't.
        """
        try:
            ut.ut_parseInt(value)
        except:
            raise ValueError(msg)

    def _checkNotUnder(self, d, path, msg):
        """
        Checks that (the real pathname of) the file with pathname 'path' is
        NOT under (the real pathname of) the directory with pathname 'd',
        raising an exception with message 'msg' if it is.
        """
        #print("---> in _checkNotUnder(%s, %s, %s)" % (d, path, msg))
        assert d is not None
        assert path is not None
        assert msg is not None
        rd = ut.ut_really(d)
        rpath = ut.ut_really(path)
        #print("   rd = [%s], rpath = [%s]" % (rd, rpath))
        self._check(not ut.ut_hasPathnamePrefix(rpath, rd), msg)

    def _check(self, condValue, msg):
        """
        Checks that 'condValue' is True, raising an exception with message
        'msg' if it isn't.
        """
        if not condValue:
            raise ValueError(msg)


# Constants.

# The default configuration instance.
__conf_instance = conf_Configuration()


# Functions.

def obtain():
    """
    Returns the single configuration instance.
    """
    result = __conf_instance
    assert result is not None
    return result


if __name__ == '__main__':
    conf = obtain()
    #conf.baseDir = "fake"
    print()
    print("Note: this is NOT a complete list of configuration information!")
    print()
    print("root dir = '%s'" % conf.rootDir)
    print("base dir = '%s'" % conf.baseDir)
    print("data dirs = [%s]" % ", ".join(conf.dataDirs))
    print()
    print("real files subdir = '%s'" % conf.realFilesSubdir)
    print("all files subdir = '%s'" % conf.allFilesSubdir)
    print("main kind+format subdir = '%s'" % conf.mainKindAndFormatSubdir)
    print()
    print("'other' dir = '%s'" % conf.otherDir)
    print("bin subdir = '%s'" % conf.binSubdir)
    print()
    print("all music filesystem mount points = '%s'" %
          str(conf.allMusicFilesystemMountPoints))
    print("all filesystem mount points = '%s'" %
          str(conf.allFilesystemMountPoints))
    print()
