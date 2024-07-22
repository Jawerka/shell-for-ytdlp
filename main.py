import os
import shutil
from urllib.request import urlopen
from urllib.request import urlretrieve
from zipfile import ZipFile


url_utilities_update = ['https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe',
                        'https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip']

default_path = os.getcwd()
utilities_path = os.path.join(default_path, 'utilities')
download_video_path = os.path.join(default_path, 'download')


def progress(uploaded, chunk, total):
    uploaded = uploaded * chunk
    percent = min((uploaded / total), 100.0)

    print(f'{(uploaded / 1048576):10.0f}/'
          f'{(total / 1048576):7.0f}MB {percent:6.1%}\r', end='')


def update_utilities(upd_url: str, work_path: str):
    """
    Функция обновления/загрузки необходимых файлов
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
                # Если размер загруженного файла отличается от размера файла в интернете
                # То загруженный файл удаляется и делается повторный вызов на загрузку

                os.remove(save_path)
                update_utilities(upd_url, work_path)
                return

            else:
                # Если размер совпадает (и это не FFMPEG),
                # то считаем что файл последней версии и просто выходим
                if 'zip' and 'ffmpeg' not in save_name:
                    return

                # Если это архив с FFMPEG, то дополнительно проверяем, распакован ли ffmpeg.exe
                if not os.path.exists(os.path.join(work_path, 'ffmpeg.exe')):
                    unzipping_ffmpeg(save_path, work_path)
                return

        # Загрузка
        print(f'Download {save_name}')
        urlretrieve(upd_url, save_path, reporthook=progress)
        print()

        if 'zip' and 'ffmpeg' in save_name:
            # Специфичное только для ffmpeg.zip
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
    Специфичное [...] для распаковки архива с FFMPEG
    распаковывает FFMPEG FFPROBE и FFPLAY в папку {utilities_path}
    для удобства дальнейшей работы
    """

    ffmpeg_file_list = [
                'ffmpeg.exe',
                'ffplay.exe',
                'ffprobe.exe']

    ffmpeg_folder_name = os.path.basename(full_path).split('.')[0]
    bin_path = os.path.join(utilities_path, ffmpeg_folder_name, 'bin')

    # Удаляем старые файлы
    for ff_file in ffmpeg_file_list:

        ff_file_path = os.path.join(utilities_path, ff_file)
        if os.path.exists(ff_file_path):
            os.remove(ff_file_path)

    ffmpeg_folder_path = os.path.join(utilities_path, ffmpeg_folder_name)
    if os.path.exists(ffmpeg_folder_path):
        shutil.rmtree(ffmpeg_folder_path)

    # Распаковка архива
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
            input(f'Введите путь сохранения, если он отличается от: {download_video_path} ')
            or download_video_path)

    if not os.path.exists(new_download_video_path):
        input(f'Введенный путь не существует, будет использован {download_video_path} ')

    else:
        download_video_path = new_download_video_path

    if not os.path.exists(download_video_path):
        os.mkdir(download_video_path)

    return download_video_path


def main():
    # Запрашиваем измнение пути сохранения
    download_path = intro(download_video_path)

    # Загружаем/обновляем утилиты
    update_loop(url_utilities_update, utilities_path)

    ytdlp_path = os.path.join(utilities_path, 'yt-dlp.exe')

    while True:

        input_url = input('Введите URL: ')

        # Проверка на доступность
        try:
            response = urlopen(input_url)

        except KeyboardInterrupt:
            input('\nKeyboard Interrupt')
            exit(0)

        except Exception as err:
            print(str(err), end=f'\n{"*"*50}\n')
            continue

        break

    key_list = [
        ytdlp_path,
        f'-P {download_path}',
        f'--ffmpeg-location {utilities_path}',
        f'--windows-filenames']

    if 'playlist' in input_url:
        key_list.append(f'-o "%(playlist)s/%(title)s [%(id)s].%(ext)s"')

    input_url = input_url.split('&')[0]
    key_list.append(input_url)
    shell_command = ' '.join(key_list)

    try:
        os.system(shell_command)

    except KeyboardInterrupt:
        input('\nKeyboard Interrupt')
        exit(0)

    except Exception as err:
        input(str(err))


main()
