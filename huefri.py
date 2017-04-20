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


class Hue(object):
    """ Class for Hue lights """

    def __init__(self, ip: str, user: str, lights: list):
        """
            Parameters
            ----------
            ip : str
                Address of Hue Bridge. DNS will be resolved.

            user : str
                The secret string generated when pairing with the Bridge.

            lights : list
                A list of IDs of Hue lights, which should be controlled.
        """
        self.ip = ip
        self.lights_selected = lights
        self.bridge = qhue.Bridge(ip, user)
        self.threads = []

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
            self.threads.append(t)
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



class Tradfri(object):
    """ Class for Tradfri lights """

    def __init__(self, ip: str, key: str, main_light: int, hue: Hue):
        """
            Parameters
            ----------
            ip : str
                Address of Tradfri gate. DNS will be resolved.

            key : str
                The secret string written on the back of the gate.

            main_lights : int
                The light we want to watch and copy changes from.

            hue: Hue
                The Hue instance we are controlling with the main light.
        """
        self.hue = hue
        self.ip = ip
        self.key = key
        self.api = pytradfri.coap_cli.api_factory(ip, key)
        self.gateway = pytradfri.gateway.Gateway(self.api)

        self.main_light = main_light

        self.color = None
        self.state = None
        self.dimmer = None

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




def main():

    """
        Get configuration for the hubs.
    """
    configfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")
    config = None
    try:
        json_data=open(configfile).read()
        config = json.loads(json_data)
    except:
        print("Can't read or parse the config. Please, create this json file next to this script.\n")
        print("FILE config.json:")
        print("""{
{
"hue":{
	"addr":"ADDR",
	"secret": "SECRET",
	"controlled": [LIST,OF,HUE,LIGHTS,TO,CONTROL (indexed from 1) ]
	},
"tradfri":{
	"addr": "ADDR",
	"secret": "SECRET",
	"main": WATCHED TRADFRI BULB (indexed from 0)
	}
}
""")
        sys.exit(1)

    hue = Hue(config['hue']['addr'],
            config['hue']['secret'],
            config['hue']['controlled'])
    tradfri = Tradfri(config['tradfri']['addr'],
            config['tradfri']['secret'],
            config['tradfri']['main'],
            hue)

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

