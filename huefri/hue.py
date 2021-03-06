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

import qhue
import datetime
import threading
from huefri.common import Hub as Hub
from huefri.common import HuefriException as HuefriException
from huefri.common import Config as Config
from huefri.common import DELTA as DELTA
from huefri.common import log as log
from huefri.common import hsb2hex as hsb2hex




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

    def changed(self):
        """ Test whether there is any change since the last call. """
        if self.tradfri is None:
            raise HuefriException("Tradfri object was not passed to Hue.")

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
                we found is likely caused by the sync and not by a manual
                control.  So, skip any operation.
            """
            log("Hue", "tradfri sync skipped")
            change = False

        return change

    def update(self):
        """ Check if the main light changed since the last call of this function
            and if yes, propagate the change to other lights.
        """

        if self.changed():
            main = self.bridge.lights[self.main_light]()['state']
            hue = main['hue']
            sat = main['sat']
            bri = main['bri']
            state = main['on']

            self.last_changed = datetime.datetime.now()
            if state:
                rgb = hsb2hex(hue, sat)
                log("Hue", "send to tradfri: %s, %s" % (rgb, str(bri)))
                self.tradfri.set_all(rgb, bri)
            else:
                rgb = hsb2hex(hue, sat)
                log("Hue", "turn off")
                self.tradfri.set_all(rgb, 0)


