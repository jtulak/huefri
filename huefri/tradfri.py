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

import time
import datetime
import os
import threading

from pytradfri import Gateway
from pytradfri.api.libcoap_api import APIFactory

from huefri.common import Hub
from huefri.common import HuefriException
from huefri.common import Config
from huefri.common import DELTA
from huefri.common import log
from huefri.common import hex2hsb
from huefri.common import hex2index
from huefri.common import COLORS_MAP
from huefri.common import UnknownColorException



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
        self.threads = []
        self.current_color_index = 0

        api_factory = APIFactory(ip)
        api_factory.psk = key
        self.api = api_factory.request
        self.gateway = Gateway()

        devices_command = self.gateway.get_devices()
        devices_commands = self.api(devices_command)
        self._devices = self.api(devices_commands)

        self.color = None
        self.state = None
        self.dimmer = None

    @classmethod
    def autoinit(cls, cnf: Config, hue: 'Hue' = None):
        """ Get the constructor arguments automatically from Config class.
            Parameters
            ----------
            hue : Hue
                The Hue instance we are controlling with the main light.
        """

        config = cnf.get()
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
            self.api(self._lights[light].light_control.set_hex_color(hex_color))
            self.api(self._lights[light].light_control.set_dimmer(brightness))
            self.api(self._lights[light].light_control.set_state(True))
        else:
            self.api(self._lights[light].light_control.set_state(False))

    def observe(self, device):
        """ A dirty hack to get the new API working """
        self.api(device.update())


    def changed(self):
        """ Test whether there is any change since the last call. """

        self.observe(self._lights[self.main_light])

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

        self.current_color_index = hex2index(color)
        if self.hue is not None:
            if self.hue.last_changed > datetime.datetime.now() - DELTA:
                """ If the other side changed within DELTA time, any change
                    we found is likely caused by the sync and not by a manual
                    control.  So, skip any operation.
                """
                log("Tradfri", "hue sync skipped")
                change = False

        return change

    def update(self):
        """ Check if the main light changed since the last call of this function
            and if yes, propagate the change to other lights.
        """
        if self.hue is None:
            raise HuefriException("Hue object was not passed to Tradfri.")
        try:
            if self.changed():
                main = self._lights[self.main_light].light_control.lights[0]

                self.last_changed = datetime.datetime.now()
                hsb = None
                if main.state:
                    hsb = hex2hsb(main.hex_color, main.dimmer)
                    hsb['on'] = True
                    log("Tradfri", "send to hue: %s" % str(hsb))
                else:
                    hsb = hex2hsb(main.hex_color, 0)
                    log("Tradfri", "turn off")
                    hsb['on'] = False
                self.hue.set_hsb(hsb)

        except UnknownColorException:
            # ignore the unknown color, only print a message
            log("Tradfri", "Unknown color, ignoring...")

    def set_color(self, color):
        """ Set all lights to color, color is a dict from COLORS_MAP """
        color = COLORS_MAP[color]['hex']
        bri = self.dimmer
        self.changed_now()
        self.set_all(color, self.dimmer)


    def set_brightness(self, brightness):
        """ Set all lights to the brightness, in range 0-100 """
        if brightness > 255:
            brightness == 255
        elif brightness < 0:
            brightness = 0

        self.changed_now()
        self.set_all(self.color, brightness)

    def color_next(self):
        self.current_color_index = (self.current_color_index + 1) % len(COLORS_MAP)
        self.set_color(self.current_color_index)

    def color_prev(self):
        self.current_color_index = (self.current_color_index - 1) % len(COLORS_MAP)
        self.set_color(self.current_color_index)

    def brightness_inc(self):
        if self.dimmer < 255:
            self.dimmer += round(254/self.brightness_steps)
            # get around the rounding error and prevent going over 100
            if self.dimmer > 230:
                self.dimmer = 255
            self.set_brightness(self.dimmer)

    def brightness_dec(self):
        if self.dimmer > 1:
            self.dimmer -= round(254/self.brightness_steps)
            # get around the rounding error and prevent going under 1
            if self.dimmer < 25:
                self.dimmer = 1
            self.set_brightness(self.dimmer)

    @property
    def _lights(self):
        return [dev for dev in self._devices if dev.has_light_control]
