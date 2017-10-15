#!/usr/bin/env python3
# vim: set expandtab cindent sw=4 ts=4:
#
# (C)2015 Jan Tulak <jan@tulak.me>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import datetime
import json
import os
import sys

DELTA = datetime.timedelta(seconds=5)

COLORS_MAP = [
        # this is for OpenHab colors
        {"hex": "efd275", # warm - 34,98 in OpenHab
            "hsb": {'on': True, 'hue':  6188, 'sat': 249}},
        {"hex": "f1e0b5", # medium - 42,59 in OpenHab
            "hsb": {'on': True, 'hue':  7644, 'sat': 150}},
        {"hex": "f5faf6", # cold - 216,5 in OpenHab
            "hsb": {'on': True, 'hue': 39312, 'sat':  13}},

        # This is for colors from official Hue app
        {"hex": "efd275", # warm - Nightlight
            "hsb": {'on': True, 'hue':  6291, 'sat': 251}},
        {"hex": "f1e0b5", # medium - Bright
            "hsb": {'on': True, 'hue':  8402, 'sat': 140}},
        {"hex": "f5faf6", # cold - Concentrate
            "hsb": {'on': True, 'hue': 39392, 'sat':  13}},
]

def hex2hsb(color_hex: str, brightness: str) -> dict:
    """ Translate hex+brightness -> hsb """

    color = None
    for c in COLORS_MAP:
        if c["hex"] == color_hex:
            color = c["hsb"]

    # nothing found = raise an exception
    if color is None:
        raise Exception("unknown color hex:%s" % color_hex)

    color['bri'] = brightness
    return color

def hsb2hex(hue: int, sat: int) -> str:
    for vals in COLORS_MAP:
        if hue == vals['hsb']['hue'] and sat == vals['hsb']['sat']:
            return vals['hex']
    raise Exception("unknown color h:%d, s:%d" % (hue, sat))

def log(where: str, s: str):
    print("[%s] %s: %s" % (str(datetime.datetime.now()), where, s))

class Hub(object):
    """ Generic hub class """

    def __init__(self, ip: str, secret: str, main_light: int, lights: list):
        """
            Parameters
            ----------
            ip : str
                Address of the hub. DNS will be resolved.

            secret : str
                The secret string generated when pairing with the bridge.

            main_lights : int
                The light we want to watch and copy changes from.

            lights : list
                A list of IDs of lights, which should be controlled.
        """
        self.last_changed = datetime.datetime.now();
        self.ip = ip
        self.secret = secret
        self.lights_selected = lights
        self.main_light = main_light

class BadConfigPathError(IOError):
    pass

class Config(object):

    _config = None

    def __init__(self):
        raise Exception("Config is a singleton, do not initializate it.")

    @classmethod
    def load_json(cls, configfile):
        """
            Populate the config object from a json file.
        """
        error = None
        try:
            with open(configfile, 'r') as h:
                json_data = h.read()
                cls._config = json.loads(json_data)
                return cls._config
        except IOError:
            error = BadConfigPathError
            log("Config", "Can't open the config. Please, create this json file next to this script.\n")
        except json.JSONDecodeError as ex:
            error = ex
            log("Config", "Can't parse the config. The file should have this syntax:\n")

        print("FILE config.json:")
        print("""{
"hue":{
	"addr":"ADDR",
	"secret": "SECRET",
	"controlled": [LIST,OF,HUE,LIGHTS,TO,CONTROL (indexed from 1) ]
	"main": WATCHED HUE BULB (indexed from 1)
	},
"tradfri":{
	"addr": "ADDR",
	"secret": "SECRET",
	"controlled": [LIST,OF,TRADFRI,LIGHTS,TO,CONTROL (indexed from 0) ]
	"main": WATCHED TRADFRI BULB (indexed from 0)
	}
}
""")
        raise error

    @classmethod
    def get(cls):
        """
            Return json object with config.
        """
        if cls._config is not None:
            return cls._config
        else:
            configfile = os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    "..",
                    "config.json")
            cls.load_json(configfile)
            return cls._config

