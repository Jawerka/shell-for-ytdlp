import os
import json
import shutil
import time

import pyperclip
from urllib.request import urlopen
from urllib.request import urlretrieve
from zipfile import ZipFile
from inputimeout import inputimeout, TimeoutOccurred

config_path = os.path.join(os.getcwd(), 'config.json')
yes_answers = ['y', 'yes', 'д', 'да']


pre_config = {
    'URL_UTILITIES_UPDATE':
        ['https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe',
         'https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip'],
    'DAFAULT_PATH': os.getcwd(),
    'UTILITIES_PATH': '',
    'DOWNLOAD_PATH': os.path.join(os.getenv('userprofile'), 'Downloads'),
    'SPONSORBLOCK_REMOVE_LIST': ['sponsor', 'selfpromo'],
    'YTDLP_PATH': '',
    'QUESTION_BYPASS': False
}

pre_config['UTILITIES_PATH'] = os.path.join(pre_config['DAFAULT_PATH'], 'utilities')
pre_config['YTDLP_PATH'] = os.path.join(pre_config['UTILITIES_PATH'], 'yt-dlp.exe')

if not os.path.exists(pre_config['DOWNLOAD_PATH']):
    pre_config['DOWNLOAD_PATH'] = pre_config['DAFAULT_PATH']

config_bkp_path = os.path.join(pre_config['UTILITIES_PATH'], 'config.bkp')

# If config.json exists, read it
if os.path.exists(config_path):
    if os.path.getsize(config_path) > 100:
        with open(config_path, 'r') as file:
            config = json.load(file)
            shutil.copyfile(config_path, config_bkp_path)

        if not config.get('QUESTION_BYPASS'):
            config['QUESTION_BYPASS'] = False
    else:
        if os.path.exists(config_bkp_path):
            if os.path.getsize(config_bkp_path) > 100:
                shutil.copyfile(config_bkp_path, config_path)
                with open(config_path, 'r') as file:
                    config = json.load(file)

                if not config.get('QUESTION_BYPASS'):
                    config['QUESTION_BYPASS'] = False

            else:
                config = pre_config.copy()
        else:
            config = pre_config.copy()

else:
    config = pre_config.copy()


def progress(uploaded, chunk, total):
    uploaded = uploaded * chunk
    percent = min((uploaded / total), 100.0)

    print(f'{(uploaded / 1048576):10.0f}/'
          f'{(total / 1048576):7.0f}MB {percent:6.1%}\r', end='')


def update_utilities(upd_url: str, work_path: str):
    """
    Function for updating/downloading necessary files
    """

    ffmpeg_file_list = [
        'ffmpeg.exe',
        'ffplay.exe',
        'ffprobe.exe']

    save_name = None
    save_path = None

    try:
        response = urlopen(upd_url)

        save_name = os.path.basename(upd_url)
        save_path = os.path.join(work_path, save_name)

        if os.path.exists(save_path):
            if 'zip' and 'ffmpeg' in save_name:
                # If it is an archive with FFMPEG, additionally check if ffmpeg.exe is unpacked.
                for ff_file in ffmpeg_file_list:
                    if not os.path.exists(os.path.join(work_path, ff_file)):
                        unzipping_ffmpeg(save_path, work_path)
                else:
                    return

            download_file_size = int(response.getheader('Content-Length').strip())

            if os.path.getsize(save_path) != download_file_size:
                # If the size of the downloaded file is different from the size of the Internet file
                # The downloaded file is deleted and the download is called again

                os.remove(save_path)
                update_utilities(upd_url, work_path)
                return

            else:
                # If the size matches (and it's not FFMPEG),
                # then assume the file is the latest version and just exit
                if 'zip' and 'ffmpeg' not in save_name:
                    return

                # If it is an archive with FFMPEG, additionally check if ffmpeg.exe is unpacked.
                if not os.path.exists(os.path.join(work_path, 'ffmpeg.exe')):
                    unzipping_ffmpeg(save_path, work_path)
                return

        # Downloading
        print(f'Download {save_name}')
        try:
            urlretrieve(upd_url, save_path, reporthook=progress)
        except Exception as err:
            input(str(err))
            exit(0)

        print()

        if 'zip' and 'ffmpeg' in save_name:
            # Specific only to ffmpeg.zip
            unzipping_ffmpeg(save_path, work_path)

    except KeyboardInterrupt:
        try:
            os.remove(save_path)
        except:
            pass

        input('\nKeyboard Interrupt')
        exit(0)

    except Exception as err:
        try:
            os.remove(save_path)
        except:
            pass

        input(str(err))


def unzipping_ffmpeg(full_path: str, utilities_path: str):
    """
    Specific [...] for unpacking a FFMPEG archive
    unpack FFMPEG FFPROBE and FFPLAY into the {utilities_path} folder
    for ease of further work
    """

    ffmpeg_file_list = [
        'ffmpeg.exe',
        'ffplay.exe',
        'ffprobe.exe']

    ffmpeg_folder_name = os.path.basename(full_path).split('.')[0]
    bin_path = os.path.join(utilities_path, ffmpeg_folder_name, 'bin')

    # Delete the old files
    for ff_file in ffmpeg_file_list:

        ff_file_path = os.path.join(utilities_path, ff_file)
        if os.path.exists(ff_file_path):
            os.remove(ff_file_path)

    ffmpeg_folder_path = os.path.join(utilities_path, ffmpeg_folder_name)
    if os.path.exists(ffmpeg_folder_path):
        shutil.rmtree(ffmpeg_folder_path)

    # Unzip the archive
    with ZipFile(full_path, 'r') as zfile:
        zfile.extractall(utilities_path)

    for ff_file in ffmpeg_file_list:
        shutil.move(os.path.join(bin_path, ff_file),
                    os.path.join(utilities_path, ff_file))

    if os.path.exists(ffmpeg_folder_path):
        shutil.rmtree(ffmpeg_folder_path)


def update_loop(url_list: str, utilities_path: str):
    for url in url_list:
        if not os.path.exists(utilities_path):
            os.mkdir(utilities_path)

        update_utilities(url, utilities_path)


def intro(download_video_path):
    new_download_video_path = (
            input(f'Enter the save path if it is different from: {download_video_path} ')
            or download_video_path)

    if not os.path.exists(new_download_video_path):
        input(f'The entered path does not exist, it will be used {download_video_path} ')

    else:
        download_video_path = new_download_video_path

    if not os.path.exists(download_video_path):
        os.mkdir(download_video_path)

    return download_video_path


def main():
    # Request to change the save path
    if not config['QUESTION_BYPASS']:
        config['DOWNLOAD_PATH'] = intro(config['DOWNLOAD_PATH'])

    # Downloading/updating utilities
    update_loop(config['URL_UTILITIES_UPDATE'], config['UTILITIES_PATH'])

    while True:
        possible_url = pyperclip.paste()

        question = 'Enter URL: '
        if 'https://' in possible_url:
            try:
                response = urlopen(possible_url)
                question = (f'\nIn your clipboard is a link: {possible_url}\n'
                            f'Press Enter if you want to download it, or enter a different URL: ')
            except:
                possible_url = ''
                pass

        if not config['QUESTION_BYPASS']:
            input_url = input(question) or possible_url
        else:
            input_url = possible_url

        # Availability check
        try:
            response = urlopen(input_url)

        except KeyboardInterrupt:
            input('\nKeyboard Interrupt')
            exit(0)

        except Exception as err:
            input(str(err))
            exit(0)

        break

    # For some unknown reason, f-string could not parse
    # direct references to dictionary elements for some users
    ytdlp_path = os.path.join(config['YTDLP_PATH'].replace('"', ''))
    download_path = os.path.join(config['DOWNLOAD_PATH'].replace('"', ''))
    utilities_path = os.path.join(config['UTILITIES_PATH'].replace('"', ''))

    ytdlp_key_list = [
        f'{ytdlp_path}',
        f'-P "{download_path}"',
        f'--continue',
        f'--retries 100',
        f'--retry-sleep 5',
        f'--ffmpeg-location "{utilities_path}"',
        f'--no-mtime',
        f'--windows-filenames',
        f'--concurrent-fragments 8']

    sponsorblock_answer = 'y'
    if not config['QUESTION_BYPASS']:
        sponsorblock_answer = input('\nRemove sponsored embeds from videos '
                                    'based on SponsorBlock base? n/[Y]: ') or 'y'

    if sponsorblock_answer == 'y':
        sponsorblock_remove = ','.join(config['SPONSORBLOCK_REMOVE_LIST'])

        ytdlp_key_list.append(f'--sponsorblock-remove {sponsorblock_remove}')

    if 'playlist' in input_url:
        ytdlp_key_list.append(f'-o "%(playlist)s/%(title)s [%(id)s].%(ext)s"')

    input_url = input_url.split('&')[0]
    ytdlp_key_list.append(input_url)
    shell_command = ' '.join(ytdlp_key_list)

    try:
        os.system(shell_command)

    except KeyboardInterrupt:
        input('\nKeyboard Interrupt')
        exit(0)

    except Exception as err:
        input(str(err))
        exit(0)

    if not config['QUESTION_BYPASS']:
        prompt = ("\nSkip all the questions next time?"
                  "\nThe link will be taken from the clipboard on startup. [N]/y: ")

        try:
            answer = inputimeout(prompt=prompt, timeout=10)
        except TimeoutOccurred:
            answer = False

        if answer:
            if any(str(answer).lower() == x for x in yes_answers):
                config['QUESTION_BYPASS'] = True
                print(f'\nConfiguration will be written to {config_path}')
                time.sleep(5)
            else:
                config['QUESTION_BYPASS'] = False
        else:
            config['QUESTION_BYPASS'] = False

    with open(config_path, 'w') as configfile:
        json.dump(config, configfile, indent=4)
        try:
            inputimeout(prompt='Done', timeout=5)
        except:
            pass


main()
