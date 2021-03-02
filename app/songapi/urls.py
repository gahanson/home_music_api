from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from .views import *

router = routers.DefaultRouter()

router.register(r'song', SongViewSet)
router.register(r'album', AlbumViewSet)
router.register(r'artist', ArtistViewSet)
router.register(r'playlist', PlaylistViewSet)
router.register(r'playlistsong', PlaylistSongViewSet)

urlpatterns = [
 path('', include(router.urls)),
 path('refresh_songs/', refresh_songs, name='refresh_songs'),
]
