from datetime import date, timedelta
import glob
import os
import subprocess
import time

# import credentials
# import photos_api


DATA_DIR = os.path.expanduser('~/usage_video_data/')
DATE_PATTERN = '%Y-%m-%d'


def make_video(input_pattern, output_fname='output.mp4'):
    cmd = (
        'ffmpeg '
        '-framerate 5 '
        '-y '  # Overwrite output file without asking.
        '-s 1920x1080 '
        f'-f image2 -pattern_type glob -i "{input_pattern}" '
        '-c:v libx264 -profile:v high -crf 20 -pix_fmt yuv420p '
        + output_fname
    )
    subprocess.run(cmd, cwd=DATA_DIR, shell=True)
    return DATA_DIR + output_fname


def main():
    # creds = credentials.get_credentials([
    #     # If modifying scopes, delete the file token.pickle.
    #     'https://www.googleapis.com/auth/photoslibrary.readonly'])
    # photos_api_instance = photos_api.PhotosApi(creds)

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    i = 0
    while True:
        # Each screenshot is ~2 MB, so taking one screenshot every 10 seconds
        # should use 2 * 6 * 60 * 12 hours/day on computer = ~8.6 GB
        subprocess.run(
            f'scrot \'{DATE_PATTERN}_{i}\' '
            + '-p',  # Take screenshot with mouse pointer.
            cwd=DATA_DIR)
        time.sleep(10)
        i += 1
        yesterday = (date.today() - timedelta(days=1)).strftime(DATE_PATTERN)
        yesterday_pattern = f'{yesterday}_*png'
        yesterday_imgs = glob.glob(f'{DATA_DIR}{yesterday_pattern}')
        if yesterday_imgs:
            make_video(yesterday_pattern, output_fname=f'{yesterday}.mp4')
            for img in yesterday_imgs:
                print(f'Removing {img}')
                # os.remove(img)


if __name__ == '__main__':
    main()
