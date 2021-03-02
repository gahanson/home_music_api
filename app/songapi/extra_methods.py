import json
import urllib
from urllib.request import pathname2url, urlretrieve

from django.apps import apps

import eyed3

from .models import Album, Artist, Song, SongApiSettings

class SongProcessing(object):

    def __GetSongFilesOnServer(self):
        """
        - retrieve list of song files on a remote file server
        - return json data consisting of a list of each file in format ['./artist/album/file_name.mp3',]
        """
        info = SongApiSettings.load()

        with urllib.request.urlopen(info.source_ip+info.source_script_path) as url:
            songsRaw = json.loads(url.read().decode())

        return songsRaw

    def __NewSongs(self, current_files, previous_files):
        """
        - compare list of songs on hard drive to a list saved from previous
        refresh
        - return list of new files on hard drive 
        """
        on_drive = current_files
        lastRun = previous_files
        returnValue = [i for i in on_drive if not i in lastRun ]

        return returnValue

    def __RemovedSongs(self, current_files, previous_files):
        """
        - compare list of songs on hard drive to a list saved from previous
        refresh
        - return list of files that are no longer on the hard drive 
        """
        on_drive = current_files
        lastRun = previous_files
        returnValue = [i for i in lastRun if not i in on_drive ]

        return returnValue

    def __AddSingleSong(self, file_path):
        """
        - add a single song file to the database
        create a url to use for playing the song in a web browser
        get an instance of the file and open it in memory
        use the file instance to extract the song metadata
        save meta data to a dictionary
        save album name to database
        save artist name to database
        save song information to database, including related album and artist info
        - return message if song has been saved to db or not
        """
        returnData = []

        info = SongApiSettings.load()
       
        song_url = info.source_ip+urllib.parse.quote(file_path[1:])

        filename, headers = urllib.request.urlretrieve(song_url)
    
        audiofile = eyed3.load(filename)

        theMetadata = {}

        if audiofile.tag.artist:
            theMetadata['artist'] = audiofile.tag.artist
        else:
            theMetadata['artist'] = "unknown"

        if audiofile.tag.album:
            theMetadata['album'] = audiofile.tag.album
        else:
            theMetadata['album'] = "unknown"

        if audiofile.tag.title:
            theMetadata['title'] = audiofile.tag.title
        else:
            theMetadata['title'] = "unknown"

        theMetadata['remote_url'] = song_url

        if Album.objects.filter(name=theMetadata['album']).exists() == False:
            albumInstance = Album.objects.create(name=theMetadata['album'])
        else:
            albumInstance = Album.objects.get(name=theMetadata['album'])

        if Artist.objects.filter(name=theMetadata['artist']).exists() == False:
            artistInstance = Artist.objects.create(name=theMetadata['artist'])
        else:
            artistInstance = Artist.objects.get(name=theMetadata['artist'])

        if Song.objects.filter(remote_url=song_url).exists() == False:
            Song.objects.create(
                album = albumInstance,
                artist = artistInstance,
                title = theMetadata['title']+'.mp3',
                remote_url = song_url,
            )
            returnData.append({"saved":file_path})
        else:
            returnData.append({"not saved":file_path})
                    
        return returnData
    
    def __DeleteSingleSong(self, file_path):
        """
        - remove a single song from the database
        """
        info = SongApiSettings.load()
        song_url = info.source_ip+urllib.parse.quote(file_path[1:])
        songInstance = Song.objects.get(remote_url=song_url)
        songInstance.delete()

        return {"deleted":file_path}
        
    def RefreshSongs(self):
        """
        compare a list of current files on the file system to a saved list 
        add new files and remove old files from database
        - return list of files added and removed
        """
        addReturnData = []
        delReturnData = []

        filesOnServer = self.__GetSongFilesOnServer()
        apiSettings = SongApiSettings.load()
        filesPresentLastRefresh = []
        if apiSettings.file_snapshot:
            filesPresentLastRefresh = json.loads(apiSettings.file_snapshot)
                
        newSongFiles = self.__NewSongs(filesOnServer, filesPresentLastRefresh)
        deletedSongs = self.__RemovedSongs(filesOnServer, filesPresentLastRefresh)
        
        if newSongFiles:
            for song in newSongFiles:
                if '.mp3' in song: 
                    addResult = self.__AddSingleSong(song)
                    addReturnData.append(addResult)
        
        if deletedSongs:
            for song in deletedSongs:
                delResult = self.__DeleteSingleSong(song)
                delReturnData.append(delResult)

        
        apiSettings.file_snapshot = json.dumps(filesOnServer)
        apiSettings.save()
        
        return {'added':addReturnData, 'deleted':delReturnData}
