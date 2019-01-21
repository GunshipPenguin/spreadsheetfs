# spreadsheetfs

Winner: Best use of Google Cloud Platform at Hack Cambridge 4D.

Mounts a FUSE virtual filesystem that stores its data as base64 encoded binary
data in a Google Sheet. Since data entered in Google sheets don't count
towards your 15GB free storage limit in Google Drive, this technically enables
you to get free unlimited cloud storage.

See the [Devpost page](https://devpost.com/software/spreadsheetfs) for
a full description.

Note that like most hackathon projects, this code was thrown together over the
course of about 15 hours in a semi-conscious state, so don't expect anything
incredibly robust.

# Setup

Ensure you have virtualenv, pip and python2 installed.

```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

# Running

Edit the constants at the beginning of `main.py` to suit your needs and run
the following to mount the FUSE filesystem and start communicating with the
Google Sheets API.

```
python main.py [mountpoint]
```

# Debugging Tips

`strace` is a good tool to use to see what filesystem related syscalls are
doing. For example, if attempts to create a file with `touch` on a
spreadsheetfs mounted on `~/mountpoint`, make sure your spreadsheetfs is
mounted and run:

```
strace touch ~/mountpoint/somefile.txt
```

# License

[MIT](https://github.com/GunshipPenguin/spreadsheetfs/blob/master/LICENSE) © Rhys Rustad-Elliott 