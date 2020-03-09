import io

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


class DriveApi(object):

    def __init__(self, creds):
        self.service = build('drive', 'v3', credentials=creds)

    def read_files(self, directory):
        """Returns dict mapping filename to lines in file for each file in
        given directory.
        """
        found_files = self._get_files_for_query(
            f"'{self.get_folder_id(directory)}' in parents")
        return {file.get('name'): self.get_file_lines(file.get('id'))
                for file in found_files}

    def get_file_lines(self, file_id):
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            # print("Downloading file %d%%." % int(status.progress() * 100))
        fh.seek(0)
        return [l.decode('utf-8') for l in fh.readlines()]

    def get_folder_id(self, folder_name):
        found_files = self._get_files_for_query(
            f"mimeType = 'application/vnd.google-apps.folder' and "
            f"name = '{folder_name}'")
        assert len(found_files) == 1, found_files
        return found_files[0].get('id')

    def _get_files_for_query(self, query):
        page_token = None
        found_files = []
        while True:
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name)',
                pageToken=page_token).execute()
            found_files += response.get('files', [])
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        return found_files
