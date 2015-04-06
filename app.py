import io
import os
import time
from os import environ
from datetime import datetime

import json
import dropbox
import requests
import flask
from flask import Flask, request

from utils import FSCache, fname_safe, mk_random_id, to_str

Undefined = object()

app = Flask(__name__)

fscache = FSCache("cache/", "cache")
SCHEDULE_JSON_URL = "https://us.pycon.org/2015/schedule/conference.json"
SCHEDULE_CACHE_SECONDS = 60 * 60 * 12

def get_dropbox_client():
    return dropbox.client.DropboxClient(environ["DROPBOX_ACCESS_TOKEN"])

def download_schedule(_, output_file):
    resp = requests.get(SCHEDULE_JSON_URL, verify=False)
    resp.raise_for_status()
    with open(output_file, "w") as f:
        for block in resp.iter_content(4096):
            f.write(block)

def get_schedule():
    data_file = fscache.get_or_create("schedule", "schedule", download_schedule)
    if time.time() - os.path.getmtime(data_file) > SCHEDULE_CACHE_SECONDS:
        os.unlink(data_file)
        return get_schedule()

    with open(data_file) as f:
        return json.load(f)

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

def save_uploaded_file(fprefix, fobj, schd_id):
    metadata = "schedule_id: %s\n" %(schd_id, )
    metadata += "release_to: %s\n" %("\n".join(request.form.getlist("release")), )
    metadata += "original_name: %s\n" %(fobj.filename, )
    metadata += "\n".join(
        "%s: %s" %(k, v)
        for (k, v) in sorted(request.environ.items())
        if not (k.startswith("wsgi.") or k.startswith("werkzeug."))
    )
    write_file(fprefix + "-log.txt", io.BytesIO(to_str(metadata)))
    fname = fprefix + to_str(os.path.splitext(fobj.filename)[1])
    res = write_file(fname, fobj)
    metadata += "\n\nresult: %r" %(res, )
    write_file(fprefix + "-log.txt", io.BytesIO(to_str(metadata)))
    return fname

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        schd_id = int(request.form["schedule_id"])
        fprefix = get_uploaded_file_name(schd_id)
        fobj = request.files["slides"]
        fname = save_uploaded_file(fprefix, fobj, schd_id)
        return flask.Response(
            "%s saved. Thanks!" %(fname, ),
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
    if not os.path.exists(".environ"):
        environ["NO_DROPBOX"] = True
        return
    with open(".environ") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            environ[k] = v

if __name__ == "__main__":
    load_environ()
    app.run(port=8812, debug=True)
