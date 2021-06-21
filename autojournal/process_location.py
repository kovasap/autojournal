import pandas as pd
import numpy as np
import datetime as DT
import os
import re
import imp
import glob
import time
import calendar
import requests
from datetime import datetime
from dateutil import tz
from bs4 import BeautifulSoup
# from mpl_toolkits.basemap import Basemap


def convert_timezone(dtime):
  """
  Convert datetimes from UTC to localtime zone
  """
  utc_datetime = datetime.strptime(dtime, "%Y-%m-%dT%H:%M:%S.%fZ")
  utc_datetime = utc_datetime.replace(tzinfo=tz.tzutc())
  local_datetime = utc_datetime.astimezone(tz.tzlocal())
  return local_datetime.strftime("%Y-%m-%d %H:%M:%S")


def process(bs):
  """
  Convert KML file into a list of dictionnaries
  At this time, every place begin with Placemark tag in the KML file
  :param bs: beautiful soup object
  :return: list of places
  """
  places = []
  for place in bs.find_all('Placemark'):
    dic = {}
    for elem in place:
      if  elem.name != 'Point':
        c = list(elem.children)
        e =  elem.find_all('Data')
        if len(c) == 1:
          dic.update({elem.name.title(): ''.join(c)})
        elif len(e) > 1:
          for d in e:
            dic.update({d.attrs['name']: d.text})
        else:
          dic.update({elem.name: [d.text for d in c]})
    places.append(dic)
  return places


def create_places_list(json_file):
  """
  Open the KML. Read the KML. Process and create json.
  :param json_file: json file path
  :return: list of places
  """
  with open(json_file, 'r') as f:
    s = BeautifulSoup(f, 'xml')
  return process(s)


def convert_time(row):
  """
  Convert datimes into well-formated dates, get event duration
  """
  b_time = datetime.strptime(row['BeginTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
  e_time = datetime.strptime(row['EndTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
  delta = (e_time - b_time).total_seconds()
  m, s = map(int,divmod(delta, 60))
  h, m = divmod(m, 60)
  row['RawBeginTime'], row['RawEndTime'] = row['BeginTime'], row['EndTime']
  row['Duration'] = '%sh %smin %ssec' % (h, m, s)
  row['IndexTime'] = row['BeginTime'] = convert_timezone(row['BeginTime'])
  row['BeginDate'], row['BeginTime'] = row['BeginTime'].split(' ')
  row['EndDate'], row['EndTime'] = convert_timezone(row['EndTime']).split(' ')
  row['WeekDay'] = datetime.strptime(row['BeginDate'], "%Y-%m-%d").weekday()
  row['TotalSecs'] = delta
  return row


def create_df(places):
  """
  Create a well formated pandas DataFrame
  One row is a event (place or moving)
  :param places: list of places
  :return: DataFrame
  """
  df = pd.DataFrame(places)
  # with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
  #   print(df)
  times = df['TimeSpan'].apply(pd.Series).rename(columns={0:'BeginTime', 1:'EndTime'})
  df = pd.concat([df, times], axis = 1)
  # df.drop(['TimeSpan', 'Email', 'Description'], axis=1, inplace=True)
  # df['Track'] = df['Track'].apply(lambda x:[d.split(' ') for d in x if d != 'clampToGround'])
  df = df.apply(convert_time, axis=1)
  return df.sort_values('IndexTime', ascending=False)


def get_kml_file(year, month, day, cookie_content, folder, overwrite=False):
  """
  Get KML file from your location history and save it in a chosen folder
  :param month: month of the location history
  :param day: day of the location history
  :param cookie_content: your cookie (see README)
  :param folder: path to the folder
  """
  cookies = dict(cookie=cookie_content)

  if type(month) == str:
    month = month[:3].title()
    cal = {v: k for k, v in enumerate(calendar.month_abbr, -1)}
    month_url = str(cal[month])
  else:
    month_url = str(int(month - 1))

  year_file = year_url = str(int(year))
  month_file = str(int(month_url) + 1)
  day_file = day_url = str(int(day))

  if len(month_file) == 1:
    month_file = '0' + month_file
  if len(day_file) == 1:
    day_file = '0' + day_file

  outfilepath = os.path.join(
    folder, f'history-{year_file}-{month_file}-{day_file}.kml')
  if not overwrite and os.path.isfile(outfilepath):
    return outfilepath
  print(f'Downloading to {outfilepath}...')

  url = 'https://www.google.com/maps/timeline/kml?authuser=0&pb=!1m8!1m3!1i{0}!2i{1}!3i{2}!2m3!1i{0}!2i{1}!3i{2}'.format(year_url, month_url, day_url)
  time.sleep(0.003 * np.random.randint(100))
  r = requests.get(url, cookies=cookies)
  if r.status_code == 200:
    with open(outfilepath, 'w') as f:
      f.write(r.text)
  else:
    print(r.text)
  return outfilepath


def full_df(kml_files):
  """
  Create a well formated DataFrame from multiple KML files
  :param folder: path to folder where are saved the KML files
  """
  df = pd.DataFrame()
  print('{0} KML files (ie {0} days) to concatenate'.format(len(kml_files)))
  for file in kml_files:
    try:
      df = pd.concat([df, create_df(create_places_list(file))])
    except KeyError as e:
      if 'TimeSpan' not in repr(e):
        raise
  df = df.sort_values('IndexTime', ascending=False)
  # Need hashable elements to drop duplicates, tuples are, list aren't
  df = df[['Address', 'BeginDate', 'BeginTime', 'RawBeginTime',
       'Category', 'Distance', 'Duration', 'EndDate', 'EndTime',
       'RawEndTime', 'IndexTime', 'Name', 'WeekDay', 'TotalSecs']]
  for elem in df.columns:
    df[elem] = df[elem].apply(lambda x: tuple([tuple(p) for p in x])
                  if type(x) is list else x)
  df.drop_duplicates(inplace=True)
  df['Distance'] = df['Distance'].apply(int)  # This is in meters.
  return df.reset_index(drop=True)


def sec_to_time(sec):
  h, s = divmod(sec, 3600)
  m, s = divmod(s, 60)
  return h, m, s, "%02d:%02d:%02d" % (h, m, s)


if __name__ == '__main__':
  output_folder = '/home/kovas/photos_calendar_sync/location_data/'
  cookie_content = 'cookie: CONSENT=YES+US.en+20180225-07-0; OTZ=5363995_84_88_104280_84_446940; OGP=-19016807:; S=billing-ui-v3=CkgJ1xHidolfyqc74Vo5xY9UmKXxuvNn:billing-ui-v3-efe=CkgJ1xHidolfyqc74Vo5xY9UmKXxuvNn:sso=aXwL3pK84fymj5WTbi7N006L6xPsxhQq; OGPC=19016807-1:19016664-5:; SEARCH_SAMESITE=CgQItI8B; ANID=AHWqTUmYIrqVeR1ZZwGqusEktPtrg2hJ8HE3Ujyb3WuME-LBzp0Uv8ZtGJlARrBU; NID=202=CK3AzGKuN3feT05S3vtaXY9OC923eX_WJoxOYuawRZ-_A4Rzw1Y3cEpGANem40umJOlZRVmgmanECPyB4lH_5q0ESnyidOOoEbW1T1u6WPf0L1UCVaZdUNL6kxg633RKmNwwtdF4JhKDxJS29bTiuayBhSLyHUZxCntv7zMGqUFYKMwZheomJjLoKnzpyyw8a_9X4QbnHdd_vqokhEnOpimZVjlAl9Rlk9pdG6ZvZ6I6EXoP7ZTHOXV1b5SGEY7rYzQ6vRaHinRI; SID=vweP0laRgn9q3QTpsrfTYutbPETFtBuOysyr8JgWiG3uhKSyY5IMAHTacjonAsaiEBcKTw.; __Secure-3PSID=vweP0laRgn9q3QTpsrfTYutbPETFtBuOysyr8JgWiG3uhKSyL-Bk9j2uozG6zKDuQBKsbw.; HSID=AbN19q3BIUA2o6Apx; SSID=AdSyw-E-fjsebVxoI; APISID=KaGUUyepjr3XehId/AZgZu9uR7Z37HtHEL; SAPISID=JhZoG03R9faqKtuC/AFieFTHgoh9KTwKKo; __Secure-HSID=AbN19q3BIUA2o6Apx; __Secure-SSID=AdSyw-E-fjsebVxoI; __Secure-APISID=KaGUUyepjr3XehId/AZgZu9uR7Z37HtHEL; __Secure-3PAPISID=JhZoG03R9faqKtuC/AFieFTHgoh9KTwKKo; 1P_JAR=2020-04-11-20; DV=w4GNKA2kSS1JMNUx7HxUEtrYZAivFlcvJBy_9KrqZAAAAFD-_UOvWji7ugAAAFjzqyMnUlHpRwAAAA; SIDCC=AJi4QfGbxHacWpHD8vDXT6VZxGhH4WiIk3S2PZ6fd59SdRdrChWABLcX1uCtIs91Yt9gc9ik3rA'
  for i in [7, 8, 9, 10, 11, 12]:
    get_kml_file(2020, 4, i, cookie_content, output_folder)
  with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
    print(full_df(output_folder))

