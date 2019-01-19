#!/usr/bin/env python
import os, errno, pprint
from googleapiclient import discovery
import fuse

sheet = "Sheet1"
google_credentials = ""
fs_spreadsheet_id = ""
sheets_service = discovery.build("sheets", "v4", developerKey=google_credentials)

if not hasattr(fuse, "__version__"):
    raise RuntimeError("Your fuse-py doesn\"t know of fuse.__version__, probably it\"s too old.")

fuse.fuse_python_api = (0, 2)


def ss_get_row(start_col, end_col, row):
    request = sheets_service.spreadsheets().values().get(spreadsheetId=fs_spreadsheet_id,
                                                         ranges='%s!%s%d:%s%d' % (sheet, start_col, row, end_col, row),
                                                         majorDimension="ROWS")
    response = request.execute()
    return response['values'][0]


def ss_get_col(col, start_row, end_row):
    request = sheets_service.spreadsheets().values().get(spreadsheetId=fs_spreadsheet_id,
                                                         range='%s!%s%d:%s%d' % (sheet, col, start_row, col, end_row),
                                                         majorDimension="COLUMNS")
    response = request.execute()
    return response['values'][0]

def ss_get_cell(cell):
    request = sheets_service.spreadsheets().values().get(spreadsheetId=fs_spreadsheet_id,
                                                         range='%s!%s' % (sheet, cell),
                                                         majorDimension="COLUMNS")
    response = request.execute()
    return response['values'][0][0]


class DefaultStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0


class File:
    def __init__(self, path, row):
        self.name = path
        self.stat = DefaultStat()
        self.row = row


class Directory:
    def __init__(self, name, row):
        self.contents = []
        self.stat = DefaultStat()
        self.name = name
        self.isdir = True
        self.row = row

    def add(self, item):
        self.contents.append(item)

    def get_item_at_path(self, path):
        target = os.path.basename(path)

        if target == ".." or target == ".":
            return Directory(path)

        for item in self.contents:
            if item.name == target:
                return item

        return None


class SpreadsheetFS(fuse.Fuse):
    def getattr(self, path):
        item = top_level_dir.get_item_at_path(path)

        if item == None:
            return -errno.ENOENT
        else:
            return item.stat

    def readdir(self, path, offset):
        for item in Directory(".", 0), Directory("..", 0), top_level_dir.contents:
            yield fuse.Direntry(item.name)

    def open(self, path, flags):
        target = top_level_dir.get_item_at_path(path)

        if target is None:
            self.create_file(path)

        return 0

    def read(self, path, size, offset):
        target = top_level_dir.get_item_at_path(path)

        if target is None:
            return -errno.ENOENT

        return self.read_file_contents(path)[offset: offset + size]

    def unlink(self, path):
        self.delete_file(path)

    def create_file(self, path):
        pass  # TODO Add API calls to create ss file

    def delete_file(self, path):
        pass  # TODO Add API calls to delete ss file

    def read_file_contents(self, path):
        pass  # TODO Add API calls to read ss file contents

    def write_file_contents(self, path):
        pass  # TODO Add API calls to write ss file contents


# Top level directory
top_level_dir = Directory("", 0)
total_files = 0


def init_fs_data():
    """
    Initializes top_level_dir and total_num_files based off spreadsheet contents.
    """
    # Get total number of files (C3)
    tot_num_files = int(ss_get_cell("C1"))

    if tot_num_files == 0:
        return

    # File names are contained on the B column
    file_name_data = ss_get_col("B", 1, tot_num_files)
    for (row_num, file_name) in enumerate(file_name_data):
        top_level_dir.contents.append(File(file_name, row_num))


def main():
    usage = """
Userspace hello example

""" + fuse.Fuse.fusage

    init_fs_data()
    server = SpreadsheetFS(version="%prog " + fuse.__version__,
                           usage=usage,
                           dash_s_do="setsingle")
    server.parse(errex=1)
    server.main()


if __name__ == "__main__":
    main()
