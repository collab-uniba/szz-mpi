import os, stat
import shutil
import pandas as pd
import glob
from typing import List


def slug_to_folder_name(slug):
    if slug is None:
        return None
    return '_____'.join(slug.split('/'))


def folder_name_to_slug(folder_name: str, join_value: str = '/'):
    if folder_name is None:
        return None
    if folder_name.endswith("/"):
        folder_name = folder_name[:-1]
    index = folder_name.rfind('/')
    if index > -1:
        folder_name = folder_name[index+1:]
    return join_value.join(folder_name.split("_____"))


def create_folder_if_not_exists(src_path: str, dest_path: str):
    if not os.path.isdir(dest_path):
        shutil.copytree(src_path, dest_path, symlinks=True)


def delete_folder_if_exists(path: str):
    if os.path.isdir(path):
        shutil.rmtree(path, onerror=__remove_readonly)


def __remove_readonly(func, path, _):
    os.chmod(path, stat.S_WRITE)
    func(path)


def read_from_folder(input_dir_path: str, pattern: str = "*.csv", usecols: List = None) -> pd.DataFrame:
    def df_from_each_file(f):
        return pd.read_csv(f, index_col=False, na_filter=False, usecols=usecols)
    return pd.concat(map(df_from_each_file, glob.glob(os.path.join(input_dir_path, pattern))), sort=False)

