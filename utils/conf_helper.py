import os.path
import re


def path_translator():
    print('Prerequisite: the current machine can see the file — either stored locally or mounted via SMB etc.\n')
    src_raw = input(
        'Enter the video file path as shown in Emby\ne.g.: /mnt/disk1/movie/movie name (2000)/a_movie_file.mkv\n').strip()
    dst_raw = input('\nEnter the corresponding folder or file path on this machine\ne.g.: E:\\movie\\movie name (2000)\n').strip()
    src_split = re.split(r'[\\/]', src_raw)
    src_keep_sep = re.split(r'([\\/])', src_raw)
    dst_split = re.split(r'[\\/]', dst_raw)
    dst_keep_sep = re.split(r'([\\/])', dst_raw)
    src_pre = ''
    dst_pre = ''
    for src_node in src_split:
        if not src_node or src_node not in dst_split:
            continue
        src_index = src_keep_sep.index(src_node)
        src_pre = ''.join(src_keep_sep[:src_index])
        dst_index = dst_keep_sep.index(src_node)
        dst_pre = ''.join(dst_keep_sep[:dst_index])
        break
    if not src_pre:
        print('\nInvalid input, please try again\n')
    else:
        print(f'\n[src] prefix:\n{src_pre}')
        print(f'\n[dst] prefix:\n{dst_pre}')
        print(f'\nConverted path:\n{os.path.normpath(src_raw.replace(src_pre, dst_pre, 1))}\n')
        return True


if __name__ == '__main__':
    while True:
        if path_translator():
            break
