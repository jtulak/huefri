#!/usr/bin/env python3
# vim: set expandtab cindent sw=4 ts=4:
#
# (C)2017 Jan Tulak <jan@tulak.me>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
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

import pytradfri
import qhue
import time
import datetime
import signal
import sys
import os
import threading
import traceback
import json

DELTA = datetime.timedelta(seconds=1)

COLORS_MAP = {
        "efd275": {'on': True, 'hue':  6188, 'sat': 249}, # warm
        "f1e0b5": {'on': True, 'hue':  7644, 'sat': 150}, # medium
        "f5faf6": {'on': True, 'hue': 39312, 'sat':  13}, # cold
}

def hex2hsb(color_hex: str, brightness: str) -> dict:
    """ Translate hex+brightness -> hsb """

    color = COLORS_MAP[color_hex]
    color['bri'] = brightness
    return color

def hsb2hex(hue: int, sat: int) -> str:
    for rgb, vals in COLORS_MAP.items():
        if hue == vals['hue'] and sat == vals['sat']:
            return rgb
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

class Hue(Hub):
    """ Class for Hue lights """

    def __init__(self, ip: str, user: str, main_light: int, lights: list, tradfri: 'Tradfri' = None):
        """
            Parameters
            ----------
            ip : str
                Address of Hue Bridge. DNS will be resolved.

            user : str
                The secret string generated when pairing with the Bridge.

            main_lights : int
                The light we want to watch and copy changes from.

            lights : list
                A list of IDs of Hue lights, which should be controlled.

            tradfri : Tradfri
                The Tradfri instance we are controlling with the main light.
        """
        super().__init__(ip, user, main_light, lights)
        self.bridge = qhue.Bridge(ip, user)

        self.hue = None
        self.bri = None
        self.sat = None
        self.state = None
        self.tradfri = tradfri

    @classmethod
    def autoinit(cls, tradfri: 'Tradfri' = None):
        """ Get the constructor arguments automatically from Config class. """
        config = Config.get()
        return cls(config['hue']['addr'],
            config['hue']['secret'],
            config['hue']['main'],
            config['hue']['controlled'],
            tradfri)

    def set_tradfri(self, tradfri: 'Tradfri'):
        self.tradfri = tradfri

    def set_hsb(self, hsb: dict):
        """ Set all controlled Hue lights to this color.

            Parameters
            ----------
            hsb : dict
                A dictionary that will be passed "as is" to the Hue REST API.
                The most important fields are: on, hue, sat, bri. See Qhue project
                description for further info.
        """
        lights = self.bridge.lights
        for l in self.lights_selected:
            t = threading.Thread(target=self._set_hsb_selected, args=(lights[l], hsb))
            t.start()

    def _set_hsb_selected(self, light, hsb: dict):
        """ Set one specific light to this color.

            Parameters
            ----------
            light : an instance of qhue ligt

            hsb : dict
                A dictionary that will be passed "as is" to the Hue REST API.
                The most important fields are: on, hue, sat, bri. See Qhue project
                description for further info.
        """
        light.state(**hsb)

    def update(self):
        """ Check if the main light changed since the last call of this function
            and if yes, propagate the change to other lights.
        """
        if self.tradfri is None:
            raise Exception("Tradfri object was not passed to Hue.")

        main = self.bridge.lights[self.main_light]()['state']

        change = False
        hue = main['hue']
        sat = main['sat']
        bri = main['bri']
        state = main['on']

        if hue != self.hue:
            change = True
            self.hue = hue
        if bri != self.bri:
            change = True
            self.bri = bri
        if sat != self.sat:
            change = True
            self.sat = sat
        if state != self.state:
            change = True
            self.state = state

        if self.tradfri.last_changed > datetime.datetime.now() - DELTA:
            """ If the other side changed within DELTA time, any change
                we found is caused by the sync and not by a manual control.
                So, skip any operation.
            """
            log("Hue", "tradfri sync skipped")
            return

        if change:
            self.last_changed = datetime.datetime.now()
            if state:
                rgb = hsb2hex(hue, sat)
                log("Hue", "send to tradfri: %s, %s" % (rgb, str(bri)))
                self.tradfri.set_all(rgb, bri)
            else:
                rgb = hsb2hex(hue, sat)
                log("Hue", "turn off")
                self.tradfri.set_all(rgb, 0)



class Tradfri(Hub):
    """ Class for Tradfri lights """

    def __init__(self, ip: str, key: str, main_light: int, lights: list, hue: 'Hue' = None):
        """
            Parameters
            ----------
            ip : str
                Address of Tradfri gate. DNS will be resolved.

            key : str
                The secret string written on the back of the gate.

            main_lights : int
                The light we want to watch and copy changes from.

            lights : list
                A list of IDs of Tradfri lights, which should be controlled.

            hue: Hue
                The Hue instance we are controlling with the main light.
        """
        super().__init__(ip, key, main_light, lights)

        self.hue = hue
        self.api = pytradfri.coap_cli.api_factory(ip, key)
        self.gateway = pytradfri.gateway.Gateway(self.api)

        self.color = None
        self.state = None
        self.dimmer = None

    @classmethod
    def autoinit(cls, hue: 'Hue' = None):
        """ Get the constructor arguments automatically from Config class.
            Parameters
            ----------
            hue : Hue
                The Hue instance we are controlling with the main light.
        """

        config = Config.get()
        return cls(config['tradfri']['addr'],
                config['tradfri']['secret'],
                config['tradfri']['main'],
                config['tradfri']['controlled'],
                hue)

    def set_hue(self, hue):
        self.hue = hue

    def set_all(self, hex_color: str, brightness: int):
        """ Set all controlled lights to specific color and brightness.

            Parameters
            ----------
            hex_color : str
                Color to set.

            brightness : int
                Brightness to set. If 0, the bulb will be turned off.
        """
        for l in self.lights_selected:
            self._set(l, hex_color, brightness)

    def _set(self, light: int, hex_color: str, brightness: int):
        """ Set given light (indexed from 0) to specific color and brightness.

            Parameters
            ----------
            light : int
                Index of the bulb, starting from 0

            hex_color : str
                Color to set.

            brightness : int
                Brightness to set. If 0, the bulb will be turned off.
        """
        if brightness:
            self._lights[light].light_control.set_hex_color(hex_color)
            self._lights[light].light_control.set_dimmer(brightness)
            self._lights[light].light_control.set_state(True)
        else:
            self._lights[light].light_control.set_state(False)


    def update(self):
        """ Check if the main light changed since the last call of this function
            and if yes, propagate the change to other lights.
        """
        if self.hue is None:
            raise Exception("Hue object was not passed to Tradfri.")

        change = False
        color = self._lights[self.main_light].light_control.lights[0].hex_color
        dimmer = self._lights[self.main_light].light_control.lights[0].dimmer
        state = self._lights[self.main_light].light_control.lights[0].state

        if dimmer != self.dimmer:
            change = True
            self.dimmer = dimmer
        if color != self.color:
            change = True
            self.color = color
        if state != self.state:
            change = True
            self.state = state

        if self.hue.last_changed > datetime.datetime.now() - DELTA:
            """ If the other side changed within DELTA time, any change
                we found is caused by the sync and not by a manual control.
                So, skip any operation.
            """
            log("Tradfri", "hue sync skipped")
            return

        if change:
            self.last_changed = datetime.datetime.now()
            if state:
                hsb = hex2hsb(self.color, self.dimmer)
                log("Tradfri", "send to hue: %s" % str(hsb))
                self.hue.set_hsb(hsb)
            else:
                hsb = hex2hsb(self.color, 0)
                log("Tradfri", "turn off")
                self.hue.set_hsb({'on': False})


    @property
    def _devices(self):
        return self.gateway.get_devices()


    @property
    def _lights(self):
        return [dev for dev in self._devices if dev.has_light_control]

class Config(object):

    _config = None

    def __init__(self):
        raise Exception("Config is a singleton, do not initializate it.")


    @classmethod
    def get(cls):
        """
            Return json object with config.
        """
        if cls._config is not None:
            return cls._config
        else:
            configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")
            try:
                json_data=open(configfile).read()
                cls._config = json.loads(json_data)
                return cls._config
            except:
                log("Config", "Can't read or parse the config. Please, create this json file next to this script.\n")
                print("FILE config.json:")
                print("""{
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
        sys.exit(1)




def main():

    hue = Hue.autoinit()
    tradfri = Tradfri.autoinit(hue)
    hue.set_tradfri(tradfri)

    """
        Forever check the main light and update Hue lights.
    """
    while True:
        try:
            tradfri.update()
            hue.update()
        except pytradfri.error.RequestTimeout:
            """ This exception is raised here and there and doesn't cause anything.
                So print just a short notice, not a full stacktrace.
            """
            log("MAIN", "Tradfri RequestTimeout().")
        except Exception as err:
            traceback.print_exc()
            log("MAIN", err)
        time.sleep(1)

if __name__ == '__main__':
    main()

