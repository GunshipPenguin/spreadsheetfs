#!/usr/bin/env python
import os, errno, pprint, stat, base64
from googleapiclient import discovery
from oauth2client import client
import fuse

sheet = "Sheet1"
fs_spreadsheet_id = ""
google_credentials = client.AccessTokenCredentials(
    access_token="",
    user_agent='ssfs')
sheets_service = discovery.build("sheets", "v4", credentials=google_credentials)

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


def ss_get_cell(col, row):
    request = sheets_service.spreadsheets().values().get(spreadsheetId=fs_spreadsheet_id,
                                                         range='%s!%s%d' % (sheet, col, row),
                                                         majorDimension="COLUMNS")
    response = request.execute()
    try:
        return response['values'][0][0]
    except KeyError: # Values not returned if cell is empty
        return ''

def ss_write_cell(col, row, data):
    range = "%s!%s%d" % (sheet, col, row)

    value_range_body = {
        "range": range,
        "majorDimension": "ROWS",
        "values": [
            [data]
        ]
    }

    request = sheets_service.spreadsheets().values().update(spreadsheetId=fs_spreadsheet_id, range=range,
                                                            valueInputOption="RAW", body=value_range_body)
    return request.execute()


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
    def truncate(self, path, length):
        target = top_level_dir.get_item_at_path(path)

        file_contents = self.read_file_contents(path)
        file_contents = file_contents[:length]

        encoded_file_contents = base64.b64encode(file_contents)
        encoded_file_contents = encoded_file_contents.decode() # Convert bytes to str
        ss_write_cell("A", target.row, encoded_file_contents)

    def getattr(self, path):
        target = top_level_dir.get_item_at_path(path)
        st = DefaultStat()

        if path == '/':
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2
        else:
            st.st_mode = stat.S_IFREG | 0o444
            st.st_nlink = 1
            st.st_size = 100
        # else:
        #     return -errno.ENOENT

        return st

    def readdir(self, path, offset):
        logfile.flush()
        for item in top_level_dir.contents:
            yield fuse.Direntry(item.name)

    def open(self, path, flags):
        target = top_level_dir.get_item_at_path(path)

        if target is None:
            self.create_file(path)

    def write(self, path, buf, offset):
        self.update_file_contents(path, buf, offset)
        return len(buf)

    def read(self, path, size, offset):
        target = top_level_dir.get_item_at_path(path)

        if target is None:
            return ''

        file_contents = self.read_file_contents(path)
        size = min(size, len(file_contents))
        offset = min(offset, len(file_contents))
        # logfile.write(str(file_contents))
        # logfile.write('\n')
        # logfile.write(str(size))
        # logfile.write('\n')
        # logfile.write(str(offset))
        # logfile.write('\n')
        # logfile.flush()
        return "".join(map(chr, file_contents[offset:offset+size]))

    def unlink(self, path):
        self.delete_file(path)

    def utimens(self, path, ts_acc, ts_mod):
        pass

    def create_file(self, path):
        increment_num_files()
        ss_write_cell("B", tot_num_files, os.path.basename(path))
        ss_write_cell("C", tot_num_files, "0")
        top_level_dir.contents.append(File(os.path.basename(path), tot_num_files))

    def delete_file(self, path):
        pass  # TODO Add API calls to delete ss file

    def read_file_contents(self, path):
        target = top_level_dir.get_item_at_path(path)
        contents = ss_get_cell("A", target.row)
        return base64.b64decode(contents)

    def update_file_contents(self, path, buf, offset):
        target = top_level_dir.get_item_at_path(path)

        # Get / unpack file contents
        curr_file_contents = self.read_file_contents(path)

        new_file_contents = curr_file_contents[:offset] + bytes(buf, encoding='ascii') + curr_file_contents[offset+len(buf):]
        new_file_contents = base64.b64encode(new_file_contents)
        new_file_contents = new_file_contents.decode() # Convert bytes to str

        ss_write_cell("A", target.row, new_file_contents)


# Top level directory
top_level_dir = Directory("", 0)
tot_num_files = 0


def increment_num_files():
    global tot_num_files
    tot_num_files += 1
    ss_write_cell("D", 1, str(tot_num_files))


def init_fs_data():
    """
    Initializes top_level_dir and total_num_files based off spreadsheet contents.
    """
    global tot_num_files
    # Get total number of files (C3)
    tot_num_files = int(ss_get_cell("D", 1))

    if tot_num_files == 0:
        return

    # File names are contained on the B column
    file_name_data = ss_get_col("B", 1, tot_num_files)
    for (row_num, file_name) in enumerate(file_name_data, start=1):
        if len(file_name) > 0:
            top_level_dir.contents.append(File(file_name, row_num))

logfile = None
def main():
    usage = """
Userspace hello example

""" + fuse.Fuse.fusage
    global logfile
    logfile = open('logfile.log', 'w')
    init_fs_data()
    server = SpreadsheetFS(version="%prog " + fuse.__version__,
                           usage=usage,
                           dash_s_do="setsingle")
    server.parse(errex=1)
    server.main()


if __name__ == "__main__":
    main()
