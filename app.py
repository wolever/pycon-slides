import io
import os
import time
import smtplib
from os import environ
from threading import Thread
from datetime import datetime
from email.mime.text import MIMEText

import json
import dropbox
import requests
import flask
from flask import Flask, request

from utils import FSCache, fname_safe, mk_random_id, to_str

Undefined = object()

app = Flask(__name__)

fscache = FSCache("cache/", "cache")
SCHEDULE_JSON_URL = "https://us.pycon.org/2016/schedule/conference.json"
SCHEDULE_CACHE_SECONDS = 60 * 60 * 12

def get_dropbox_client():
    return dropbox.client.DropboxClient(environ["DROPBOX_ACCESS_TOKEN"])

def send_email(recips, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = "wolever@pycon.ca"
    msg['To'] = ", ".join(recips)

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.SMTP(
        environ["MAILGUN_SMTP_SERVER"],
        int(environ["MAILGUN_SMTP_PORT"]),
    )
    s.starttls()
    s.login(environ["MAILGUN_SMTP_LOGIN"], environ["MAILGUN_SMTP_PASSWORD"])
    s.sendmail(msg['From'], recips, msg.as_string())
    s.quit()


def download_schedule(_, output_file):
    resp = requests.get(SCHEDULE_JSON_URL, verify=False)
    resp.raise_for_status()
    with open(output_file, "w") as f:
        for block in resp.iter_content(4096):
            f.write(block)

def _get_schedule():
    data_file = fscache.get_or_create("schedule", "schedule", download_schedule)
    if time.time() - os.path.getmtime(data_file) > SCHEDULE_CACHE_SECONDS:
        os.unlink(data_file)
        return get_schedule()

    with open(data_file) as f:
        return json.load(f)

def get_schedule():
    schedule = _get_schedule()
    return [
        {
            "abstract": "",
            "authors": [
                "TODO: ADD KEYNOTES",
            ],
            "conf_key": 100000,
            "contact": [
                "TODO: ADD KEYNOTES",
            ],
            "description": "Keynote",
            "duration": 30,
            "start": "2015-04-10T09:00:00",
            "end": "2015-04-10T090:30:00",
            "kind": "keynote",
            "license": "CC",
            "name": "TODO: ADD KEYNOTES",
            "released": True,
            "room": "TODO: ADD KEYNOTES",
            "tags": ""
        },
    ] + schedule


def schedule_item_file_prefix(item):
    start = datetime.strptime(item["start"], "%Y-%m-%dT%H:%M:%S")
    dest_dir = fname_safe("%s - %s" %(
        start.strftime("%a"),
        item["room"],
    ))
    dest_name = fname_safe("%s - %s - %s" %(
        start.strftime("%Hh%M"),
        ", ".join(sorted(item["authors"])),
        item["name"],
    ))[:80]
    return "%s/%s" %(dest_dir, dest_name)

def get_uploaded_file_name(schedule_id):
    for item in get_schedule():
        if item["conf_key"] == schedule_id:
            break
    else:
        raise Exception("Bad schedule ID: %r" %(schedule_id, ))
    prefix = schedule_item_file_prefix(item)
    return "%s-%s" %(prefix, mk_random_id())

def write_file(target, fobj):
    if environ.get("NO_DROPBOX"):
        with open(os.path.join(fscache.basedir, target.replace("/", "--")), "w") as f:
            while True:
                hunk = fobj.read(4096)
                if not hunk:
                    break
                f.write(hunk)
        return
    db = get_dropbox_client()
    res = db.put_file(target, fobj, overwrite=True)
    print target, "-->", res
    return res

def save_uploaded_file_real(fname_list, fprefix, fobj, filename, schd_id, release, environ_items):
    fname = fprefix + to_str(os.path.splitext(filename)[1])
    fname_list.append(fname)

    try:
        metadata = "schedule_id: %s\n" %(schd_id, )
        metadata += "release_to: %s\n" %(",".join(release), )
        metadata += "original_name: %s\n" %(filename, )
        metadata += "\n".join(
            "%s: %s" %(k, v)
            for (k, v) in sorted(environ_items)
            if not (k.startswith("wsgi.") or k.startswith("werkzeug."))
        )
        write_file(fprefix + "-log.txt", io.BytesIO(to_str(metadata)))
        res = write_file(fname, fobj)
        metadata += "\n\nresult: %r" %(res, )
        write_file(fprefix + "-log.txt", io.BytesIO(to_str(metadata)))
    finally:
        fobj.close()

    if not environ.get("NO_DROPBOX"):
        db = get_dropbox_client()
        share = db.media(res["path"])
        send_email(
            [x.strip() for x in os.environ["MAIL_RECIPIENTS"].split(",")],
            "New PyCon slide upload",
            "\n".join([
                "New file: %s" %(fname, ),
                "Download: %s" %(share["url"], ),
                "Original file name: %s" %(filename, ),
            ]),
        )

def save_uploaded_file(fprefix, fobj, schd_id):
    release = request.form.getlist("release")
    environ_items = request.environ.items()
    fname_list = []
    # weee this can fail and we'll have noooooo idea and this is terrible :D
    # TODO: fix that...
    # NB: need to do this in the background because Heroku likes its workers to
    # respond quickly, but saving to dropbox can be a bit slow.
    temp_fname = "/tmp/temp-upload-%s" %(mk_random_id(), )
    fobj.save(temp_fname)
    temp_fobj = open(temp_fname)
    thread = Thread(
        target=save_uploaded_file_real,
        args=(fname_list, fprefix, temp_fobj, fobj.filename, schd_id, release, environ_items),
    )
    os.unlink(temp_fname)
    thread.start()
    thread.join(10)
    if thread.is_alive():
        return None
    return fname_list[0]

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        schd_id = int(request.form["schedule_id"])
        fprefix = get_uploaded_file_name(schd_id)
        fobj = request.files["slides"]
        fname = save_uploaded_file(fprefix, fobj, schd_id)
        return flask.Response(
            "%s saved. Thanks!" %(fname or "File", ),
            content_type="text/plain",
        )

    resp = flask.make_response(
        flask.render_template(
            "index.html",
            schedule=get_schedule(),
        )
    )
    if "client_id" not in request.cookies:
        resp.set_cookie("client_id", mk_random_id())
    return resp

def load_environ():
    env_file = os.path.join(os.path.dirname(__file__), ".environ")
    if not os.path.exists(env_file):
        environ["NO_DROPBOX"] = True
        return
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            environ[k] = v


load_environ()

if __name__ == "__main__":
    app.run(port=8812, debug=True)
