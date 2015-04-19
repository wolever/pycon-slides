import json

def get_schedule():
    schedule = json.load(open("schedule.json"))
    return [
        {
            "abstract": "",
            "authors": [
                "Julia Evans",
            ],
            "conf_key": 100000,
            "contact": [
                "julia@jvns.ca",
            ],
            "description": "Keynote",
            "duration": 30,
            "start": "2015-04-10T09:00:00",
            "end": "2015-04-10T090:30:00",
            "kind": "keynote",
            "license": "CC",
            "name": "Keynote",
            "released": True,
            "room": "Room 517AB",
            "tags": ""
        },
        {
            "abstract": "",
            "authors": [
                "Catherine Bracy",
            ],
            "conf_key": 100001,
            "contact": [
                "bracy@codeforamerica.org",
            ],
            "description": "Keynote",
            "duration": 40,
            "start": "2015-04-10T09:30:00",
            "end": "2015-04-10T10:10:00",
            "kind": "keynote",
            "license": "CC",
            "name": "Keynote",
            "released": True,
            "room": "Room 517AB",
            "tags": ""
        },
        {
            "abstract": "",
            "authors": [
                "Guido van Rossum",
            ],
            "conf_key": 100002,
            "contact": [
                "guido@python.org",
            ],
            "description": "Keynote",
            "duration": 40,
            "start": "2015-04-11T09:00:00",
            "end": "2015-04-11T09:40:00",
            "kind": "keynote",
            "license": "CC",
            "name": "Keynote (Saturday)",
            "released": True,
            "room": "Room 517AB",
            "tags": ""
        },
        {
            "abstract": "",
            "authors": [
                "Gabriella Coleman",
            ],
            "conf_key": 100003,
            "contact": [
                "gabriella.coleman@mcgill.ca",
            ],
            "description": "Keynote",
            "duration": 40,
            "start": "2015-04-11T09:40:00",
            "end": "2015-04-11T10:20:00",
            "kind": "keynote",
            "license": "CC",
            "name": "Keynote",
            "released": True,
            "room": "Room 517AB",
            "tags": ""
        },
        {
            "abstract": "",
            "authors": [
                "Van Lindberg",
            ],
            "conf_key": 100004,
            "contact": [
                "van.lindberg@gmail.com",
            ],
            "description": "Keynote",
            "duration": 20,
            "start": "2015-04-12T09:00:00",
            "end": "2015-04-12T09:20:00",
            "kind": "keynote",
            "license": "CC",
            "name": "Keynote",
            "released": True,
            "room": "Room 517AB",
            "tags": ""
        },
        {
            "abstract": "",
            "authors": [
                "Jacob Kaplan-Moss",
            ],
            "conf_key": 100005,
            "contact": [
                "jacob@jacobian.org",
            ],
            "description": "Keynote",
            "duration": 40,
            "start": "2015-04-12T09:20:00",
            "end": "2015-04-12T10:00:00",
            "kind": "keynote",
            "license": "CC",
            "name": "Keynote",
            "released": True,
            "room": "Room 517AB",
            "tags": ""
        },
        {
            "abstract": "",
            "authors": [
                "Guido van Rossum",
            ],
            "conf_key": 100006,
            "contact": [
                "guido@python.org",
            ],
            "description": "Keynote",
            "duration": 40,
            "start": "2015-04-12T15:10:00",
            "end": "2015-04-12T15:50:00",
            "kind": "keynote",
            "license": "CC",
            "name": "Type Hints",
            "released": True,
            "room": "Room 517AB",
            "tags": ""
        },
        {
            "abstract": "",
            "authors": [
                "Gary Bernhardt",
            ],
            "conf_key": 100007,
            "contact": [
                "gary.bernhardt@gmail.com",
            ],
            "description": "Keynote",
            "duration": 40,
            "start": "2015-04-12T15:50:00",
            "end": "2015-04-12T16:30:00",
            "kind": "keynote",
            "license": "CC",
            "name": "Keynote",
            "released": True,
            "room": "Room 517AB",
            "tags": ""
        },
    ] + schedule

