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
        # This is for colors from official Hue app
        {"hex": "efd275", # warm - Nightlight
            "hsb": {'on': True, 'hue':  6291, 'sat': 251}},
        {"hex": "f1e0b5", # medium - Bright
            "hsb": {'on': True, 'hue':  8402, 'sat': 140}},
        {"hex": "f5faf6", # cold - Concentrate
            "hsb": {'on': True, 'hue': 39392, 'sat':  13}},
]

def hex2index(color_hex: str) -> int:
    for i,c in enumerate(COLORS_MAP):
        if c["hex"] == color_hex:
            return i
    raise UnknownColorException("unknown color hex:%s" % color_hex)

def hsb2index(hue: int, sat: int) -> str:
    for i, vals in enumerate(COLORS_MAP):
        if hue == vals['hsb']['hue'] and sat == vals['hsb']['sat']:
            return i
    raise UnknownColorException("unknown color h:%d, s:%d" % (hue, sat))

def hex2hsb(color_hex: str, brightness: str) -> dict:
    """ Translate hex+brightness -> hsb """
    color = COLORS_MAP[hex2index(color_hex)]['hsb']
    color['bri'] = brightness
    return color

def hsb2hex(hue: int, sat: int) -> str:
    return COLORS_MAP[hsb2index(hue, sat)]['hex']

def log(where: str, s: str):
    print("[%s] %s: %s" % (str(datetime.datetime.now()), where, s))

class HuefriException(Exception):
    pass

class UnknownColorException(HuefriException):
    pass

class Hub(object):
    """ Generic hub class """
    brightness_steps = 8

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
        self.changed_now()
        self.ip = ip
        self.secret = secret
        self.lights_selected = lights
        self.main_light = main_light

    def changed_now(self):
        self.last_changed = datetime.datetime.now()

    def color_next(self):
        raise NotImplementedError

    def color_prev(self):
        raise NotImplementedError

    def brightness_inc(self):
        raise NotImplementedError

    def brightness_dec(self):
        raise NotImplementedError

    def set_color(self, color):
        """ Set all lights to color, color a dict from COLORS_MAP """
        raise NotImplementedError

    def set_brightness(self, brightness):
        """ Set all lights to the brightness, in range 0-100 """
        raise NotImplementedError

class BadConfigPathError(IOError):
    pass

class Config(object):

    path = None
    _loaded = False
    _state = None

    def __init__(self):
        raise Exception("Config is a singleton, do not initializate it.")

    @classmethod
    def get(cls):
        """
            Populate the config object from a json file.
        """
        error = None
        if cls._state is not None:
            return cls._state
        try:
            with open(cls.path, 'r') as h:
                json_data = h.read()
                cls._state = json.loads(json_data)
        except IOError:
            error = BadConfigPathError
            log("Config",
                "Can't open the config '%s'. Please, create a json file next to this script.\n" %
                cls.path)
        except json.JSONDecodeError as ex:
            error = ex
            log("Config", "Can't parse the config.\n")

        if error:
            log("Config", """File config.json should contain:
{
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
        return cls._state
