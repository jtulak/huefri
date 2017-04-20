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

def hex2hsb(color_hex: str, brightness: str) -> dict:
    """ Translate hex+brightness -> hsb """

    COLORS_MAP = {
            "efd275": {'on': True, 'hue':  6188, 'sat': 249}, # warm
            "f1e0b5": {'on': True, 'hue':  7644, 'sat': 150}, # medium
            "f5faf6": {'on': True, 'hue': 39312, 'sat':  13}, # cold
    }
    color = COLORS_MAP[color_hex]
    color['bri'] = brightness
    return color

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
        self.ip = ip
        self.secret = secret
        self.lights_selected = lights
        self.main_light = main_light

class Hue(Hub):
    """ Class for Hue lights """

    def __init__(self, ip: str, user: str, main_light: int, lights: list):
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
        """
        super().__init__(ip, user, main_light, lights)
        self.bridge = qhue.Bridge(ip, user)

    @classmethod
    def autoinit(cls):
        """ Get the constructor arguments automatically from Config class. """
        config = Config.get()
        return cls(config['hue']['addr'],
            config['hue']['secret'],
            config['hue']['main'],
            config['hue']['controlled'])

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



class Tradfri(Hub):
    """ Class for Tradfri lights """

    def __init__(self, ip: str, key: str, main_light: int, lights: list, hue: Hue):
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
    def autoinit(cls, hue: Hue):
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


    def set(self, light: int, hex_color: str, brightness: int):
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
        change = False
        color = self._lights[self.main_light].light_control.lights[0].hex_color
        dimmer = self._lights[self.main_light].light_control.lights[0].dimmer
        state = self._lights[self.main_light].light_control.lights[0].state

        if dimmer != self.dimmer:
            change = True
            print("Dimmer changed to: %s" % dimmer)
            self.dimmer = dimmer
        if color != self.color:
            change = True
            print("Color changed to: %s" % color)
            self.color = color
        if state != self.state:
            change = True
            print("State changed to: %s" % state)
            self.state = state

        if change:
            if state:
                hsb = hex2hsb(self.color, self.dimmer)
                print("send to hue: %s" % str(hsb))
                self.hue.set_hsb(hsb)
            else:
                hsb = hex2hsb(self.color, 0)
                print("turn off")
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
                print("Can't read or parse the config. Please, create this json file next to this script.\n")
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

    """
        Forever check the main light and update Hue lights.
    """
    while True:
        try:
            print(datetime.datetime.now())
            tradfri.update()
        except Exception as err:
            traceback.print_exc()
            print(err)
        time.sleep(1)

if __name__ == '__main__':
    main()

