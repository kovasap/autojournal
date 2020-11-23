from datetime import datetime
import glob
import os
import subprocess
import time

# import credentials
# import photos_api


DATA_DIR = os.path.expanduser('~/usage_video_data/')
DATE_PATTERN = '%Y-%m-%d'
IDLE_TIMEOUT_MINS = 15


def make_video(input_img_pattern, output_fname='output.mp4'):
    cmd = ['ffmpeg',
           '-framerate', '5',
           '-y',  # Overwrite output file without asking.
           '-s', '1920x1080',
           '-i', input_img_pattern,
           '-c:v', 'libx264', '-profile:v', 'high', '-crf', '20',
           '-pix_fmt', 'yuv420p',
           output_fname]
    subprocess.run(cmd, cwd=DATA_DIR)
    return DATA_DIR + output_fname


def main():
    # creds = credentials.get_credentials([
    #     # If modifying scopes, delete the file token.pickle.
    #     'https://www.googleapis.com/auth/photoslibrary.readonly'])
    # photos_api_instance = photos_api.PhotosApi(creds)

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    i = 0
    active = True
    while True:
        idle_ms = int(subprocess.run(['xprintidle'],
                                     capture_output=True).stdout)
        if idle_ms / 1000 / 60 > IDLE_TIMEOUT_MINS:
            if active:
                i = 0
                imgs = glob.glob(f'{DATA_DIR}*.png')
                if imgs:
                    make_video(
                        f'%05d.png',
                        f'{datetime.now().strftime("%Y-%m-%d_%H:%M")}.mp4')
                    for img in imgs:
                        print(f'Removing {img}')
                        os.remove(img)
                active = False
        else:
            active = True
            # Each screenshot is ~2 MB, so taking one screenshot every 10
            # seconds should use 2 * 6 * 60 * 12 hours/day on computer = ~8.6
            # GB
            subprocess.run(
                ['scrot',
                 f'{DATA_DIR}{i:05}.png',
                 '-p',  # Take screenshot with mouse pointer.
                 '-o',  # Overwrite existing files (if program was restarted).
                 ])
            i += 1
        time.sleep(10)


if __name__ == '__main__':
    main()
