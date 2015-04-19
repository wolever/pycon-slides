#!/usr/bin/env python
import os
import sys
import shutil
import zipfile
from itertools import islice

from bs4 import BeautifulSoup
from robobrowser import RoboBrowser
from robobrowser.forms import fields

from schedule import get_schedule

class SpeakerDeckBrowser(RoboBrowser):
    def __init__(self, email, password, *args, **kwargs):
        super(SpeakerDeckBrowser, self).__init__(*args, **kwargs)
        self._email = email
        self._password = password

    def login(self):
        self.open('https://speakerdeck.com/signin')
        form = self.get_form(action='/sessions')
        form['email'].value = self._email
        form['password'].value = self._password
        self.submit_form(form)

    def upload(self, path, title, desc=""):
        self.open('https://speakerdeck.com/new')
        s3_form = self.get_form('s3-uploader')
        sd_form = self.get_form('upload_talk')

        # The Content-Type parameter seems necessary to get a successful response from S3.
        input = BeautifulSoup('<input name="Content-Type" value="application/pdf">').find("input")
        s3_form.add_field(fields.Input(input))
        s3_form['file'] = open(path, 'rb')

        # Had trouble submitting the forms with RoboBrowser, so sneak under and use requests.
        print "Posting %s to S3..." %(path, )
        res = self.session.post(s3_form.action, **s3_form.serialize().to_requests(method='post'))
        sd_form['talk[name]'] = title
        sd_form['talk[description]'] = desc
        sd_form['talk[view_policy]'] = 'public'
        sd_form['talk[published_at]'] = '2015/04/18'
        sd_form['talk[category_id]'] = '7' # programming
        params = sd_form.serialize().to_requests(method='post')

        # For some reason, this field seems to be set by JS somewhere.
        print "Creating deck on speakerdeck..."
        params['data'].append(('talk[pdf_filename]', os.path.basename(path)))
        res2 = self.session.post('https://speakerdeck.com/new.json', **params)


class Deck(object):
    def __init__(self, log_file, deck_file):
        self.log_file = log_file
        self.deck_file = deck_file
        with open(log_file) as f:
            self.log = dict(
                [y.strip() for y in x.split(": ", 1)]
                for x in f if ": " in x
            )
            f.seek(0)
            for line in islice(f, 5):
                if line == "speakerdeck\n":
                    self.log["release_to"] += "speakerdeck"
        self.released = "speakerdeck" in self.get("release_to")
        self.id = int(self.get("schedule_id"))
        self.file_ext = os.path.splitext(self.deck_file)[1]

    def get(self, attr):
        return self.log.get(attr)

    def set(self, attr, val):
        with open(self.log_file, "r+") as f:
            f.seek(-1, 2)
            if f.read() != "\n":
                f.write("\n")
            f.write("%s: %s\n" %(attr, val))
        self.log[attr] = val

def list_decks(basedir):
    log_file = None
    for base, _, files in os.walk(basedir):
        for f in files:
            f = os.path.join(base, f)
            log_file = os.path.splitext(f)[0] + "-log.txt"
            if os.path.exists(log_file):
                yield Deck(log_file, f)

def load_decks():
    decks_by_id = {}
    for deck in list_decks(DECK_DIR):
        decks_by_id.setdefault(deck.id, []).append(deck)
    for id, decks in decks_by_id.items():
        decks.sort(key=lambda x: x.deck_file)
    return decks_by_id

def _copy_deck_zipfile(target, deck_file):
    if os.path.exists(target):
        shutil.rmtree(target)
    os.mkdir(target)
    with zipfile.ZipFile(deck_file) as zf:
        to_extract = [
            f for f in zf.namelist()
            if not f.startswith("__MACOSX")
        ]
        prefixes = [x.partition("/")[0] for x in to_extract]
        use_common_prefix = (
            len(prefixes) > 1 and
            len(set(prefixes)) == 1
        )
        common_prefix = len((prefixes[0] + "/") if use_common_prefix else "")
        for member in to_extract:
            stripped = member[common_prefix:]
            if not stripped:
                continue
            stripped = "/".join(
                x for x in stripped.split("/")
                if x not in (".", "..")
            )
            print member, "-->", stripped
            outf_name = "%s/%s" %(target, stripped)
            upperdirs = os.path.dirname(outf_name)
            if upperdirs and not os.path.exists(upperdirs):
                os.makedirs(upperdirs)
            if stripped[-1] == '/':
                if not os.path.isdir(outf_name):
                    os.mkdir(outf_name)
            else:
                with zf.open(member) as source, \
                     open(outf_name, "wb") as outf:
                    shutil.copyfileobj(source, outf)

def copy_deck_to_github(deck):
    if deck.file_ext == ".pdf":
        return
    slot = SCHEDULE[deck.id]
    dirname = "%s - %s" %(", ".join(slot["authors"]), slot["name"])
    dirname = dirname.replace("/", "-")
    target = os.path.join(GITHUB_DIR, dirname).rstrip(".")
    if deck.deck_file.endswith(".zip"):
        _copy_deck_zipfile(target, deck.deck_file)
    else:
        target_file = target + deck.file_ext
        shutil.copyfile(deck.deck_file, target_file)

def copy_deck_to_speakerdeck(browser, deck):
    if deck.file_ext != ".pdf":
        return
    if deck.get("did_speakerdeck_upload"):
        return
    slot = SCHEDULE[deck.id]
    title = "%s - %s" %(", ".join(slot["authors"]), slot["name"])
    browser.upload(
        deck.deck_file,
        title=title,
        desc=slot["description"] + ("\n\n" + slot["conf_url"] if "conf_url" in slot else ""),
    )
    deck.set("did_speakerdeck_upload", "true")

def summarize_decks(deck_groups):
    for id, decks in deck_groups.items():
        print "%s: %s" %(
            id,
            "; ".join(
                ("%s" if deck.released else "(%s)") %(deck.file_ext, )
                for deck in decks
            ),
        )

def main():
    if not os.path.exists("login.txt"):
        print "Error: create a login.txt which contains the username and password"
        print "       $ echo 'username password' > login.txt"
        return 1
    with open("login.txt") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                continue
            user, password = line.split()
    browser = SpeakerDeckBrowser(user, password)
    browser.login()
    deck_groups = load_decks()
    #summarize_decks(decks)
    for id, decks in deck_groups.items():
        released = [ d for d in decks if d.released ]
        if not released:
            continue
        deck = released[-1]
        copy_deck_to_github(deck)
        copy_deck_to_speakerdeck(browser, deck)

DECK_DIR = "/Users/wolever/Dropbox/Apps/pycon-2015-slides/"
GITHUB_DIR = "/Users/wolever/code/pycon-2015-slides/"
SCHEDULE = {}
for item in get_schedule():
    SCHEDULE[item["conf_key"]] = item

if __name__ == '__main__':
    sys.exit(main())
