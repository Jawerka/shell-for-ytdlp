import os
import shutil
from urllib.request import urlopen
from urllib.request import urlretrieve
from zipfile import ZipFile


url_utilities_update = ['https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe',
                        'https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip']


download_path = os.path.join(os.getenv('userprofile'), 'Downloads')
default_path = os.getcwd()
utilities_path = os.path.join(default_path, 'utilities')
download_video_path = os.path.join(download_path, 'youtube')

sponsorblock_remove_list = ['sponsor', 'selfpromo']
ytdlp_path = os.path.join(utilities_path, 'yt-dlp.exe')


def progress(uploaded, chunk, total):
    uploaded = uploaded * chunk
    percent = min((uploaded / total), 100.0)

    print(f'{(uploaded / 1048576):10.0f}/'
          f'{(total / 1048576):7.0f}MB {percent:6.1%}\r', end='')


def update_utilities(upd_url: str, work_path: str):
    """
    Function for updating/downloading necessary files
    """

    save_name = None
    save_path = None

    try:
        response = urlopen(upd_url)

        save_name = os.path.basename(upd_url)
        save_path = os.path.join(work_path, save_name)

        if os.path.exists(save_path):
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
    if not os.path.exists(download_video_path):
        os.mkdir(download_video_path)

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
    download_path = intro(download_video_path)

    # Downloading/updating utilities
    update_loop(url_utilities_update, utilities_path)

    while True:

        input_url = input('Введите URL: ')

        # Availability check
        try:
            response = urlopen(input_url)

        except KeyboardInterrupt:
            input('\nKeyboard Interrupt')
            exit(0)

        except Exception as err:
            print(str(err), end=f'\n{"*"*50}\n')
            continue

        break

    ytdlp_key_list = [
        ytdlp_path,
        f'-P {download_path}',
        f'--ffmpeg-location {utilities_path}',
        f'--windows-filenames',
        f'--concurrent-fragments 8']

    sponsorblock_answer = input('Remove sponsored embeds from videos '
                                'based on SponsorBlock base? n/[y]: ') or 'y'

    if sponsorblock_answer == 'y':
        sponsorblock_remove = ','.join(sponsorblock_remove_list)

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


main()
