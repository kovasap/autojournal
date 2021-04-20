from typing import List
import functools
from googleapiclient.discovery import build


# https://developers.google.com/photos/library/reference/rest/v1/mediaItems
mediaItem = dict

# Helpful tips at
# https://stackoverflow.com/questions/50573196/access-google-photo-api-with-python-using-google-api-python-client


class PhotosApi(object):

    def __init__(self, creds):
        self.service = build('photoslibrary', 'v1', credentials=creds)

    def get_album_id(self, name: str) -> str:
        results = self.service.albums().list(
            pageSize=10, fields="nextPageToken,albums(id,title)").execute()
        for album in results.get('albums', []):
            if album['title'] == name:
                return album['id']
        else:
            raise Exception(f'Album {name} not found!')

    def get_album_contents(self, album_id: str) -> List[mediaItem]:
        photos = []
        page_token = None
        while page_token != '':
            page_token = '' if not page_token else page_token
            results = self.service.mediaItems().search(
                body=dict(pageSize=25, pageToken=page_token,
                          albumId=album_id)
            ).execute()
            photos += results.get('mediaItems', [])
            page_token = results.get('nextPageToken', '')
        return photos
