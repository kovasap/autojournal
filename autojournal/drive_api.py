import csv
import os.path as op
import io
import zipfile

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from . import utils


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

  def read_all_spreadsheet_data(self, directory, only=None):
    """Gets all spreadsheet data from directory.

    If the set only is specified, will only get files whose name appears in
    the only set.
    """
    found_files = self._get_files_for_query(
        f"'{self.get_folder_id(directory)}' in parents")
    return {file.get('name'): self.get_spreadsheet_data(file)
            for file in found_files
            if only is None or file.get('name') in only}

  def get_spreadsheet_data(self, file):
    if file['mimeType'] not in {
        'text/comma-separated-values', 'text/csv', 'application/zip',
        'text/tab-separated-values'}:
      print(f'File {file} not of supported type.')
      return []
    delimiter = ','
    if file['mimeType'] == 'text/tab-separated-values':
      delimiter = '\t'
    get_media_kwargs = {}
    if file['mimeType'] == 'application/vnd.google-apps.spreadsheet':
      get_media_kwargs['mimeType'] = 'text/csv'
      # get_media_kwargs['exportFormat'] = 'csv'
      # get_media_kwargs['gid'] = '0'
    dl_file = utils.retry_on_error(
        lambda: self.download_file(file.get('id'), **get_media_kwargs))
    if file['mimeType'] == 'application/zip':
      dl_file = zipfile.ZipFile(dl_file).open(
          op.splitext(file.get('name'))[0] + '.csv')
    textio = io.TextIOWrapper(dl_file, encoding='utf-8')
    return [row for row in csv.DictReader(textio, delimiter=delimiter)]

  def download_file(self, file_id, **get_media_kwargs):
    request = self.service.files().get_media(
        fileId=file_id, **get_media_kwargs)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
      status, done = downloader.next_chunk()
      # print("Downloading file %d%%." % int(status.progress() * 100))
    fh.seek(0)
    return fh

  def download_file_to_disk(self, folder, filename, filepath):
    folder_id = self.get_folder_id(folder)
    for file in self._get_files_for_query(f"'{folder_id}' in parents"):
      if file['name'] == filename:
        with open(filepath, 'wb') as f:
          f.write(self.download_file(file['id']).getbuffer())

  def get_file_lines(self, file_id):
    return [ln.decode('utf-8')
            for ln in self.download_file(file_id).readlines()]

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
      response = utils.retry_on_error(
          self.service.files().list(
              q=query,
              spaces='drive',
              fields='nextPageToken, files(id, name, mimeType)',
              pageToken=page_token).execute)
      found_files += response.get('files', [])
      page_token = response.get('nextPageToken', None)
      if page_token is None:
        break
    return found_files


if __name__ == "__main__":
  import credentials
  creds = credentials.get_credentials([
      # If modifying scopes, delete the file token.pickle.
      'https://www.googleapis.com/auth/drive.readonly'])
  drive_api = DriveApi(creds)
