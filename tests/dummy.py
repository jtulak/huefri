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
from huefri.common import DELTA as DELTA

class DummyHub(object):
    """ mock of Hue and Tradfri classes """
    def __init__(self):
        self.set_time_to_now()
        self.rgb = None
        self.bri = None
        self.hsb = None

    def set_time_to_now(self):
        """ test method to manipulate with last_changed time """
        self.last_changed = datetime.datetime.now()

    def set_time_to_past(self):
        """ test method to manipulate with last_changed time """
        self.last_changed = datetime.datetime.now() - 2*DELTA


    def set_all(self, rgb, bri):
        """ Tradfri method """
        self.rgb = rgb
        self.bri = bri

    def set_hsb(self, hsb):
        """ Hue method """
        self.hsb = hsb


# Hue section
class HLight(object):
    def __init__(self):
        self.hsb = None

    def state(self, hue, sat, bri):
        self.hsb = {'hue': hue, 'sat': sat, 'bri': bri}

    def __call__(self):
        if self.hsb is None:
            return {'state': {'hue': 0, 'sat': 0, 'bri': 0, 'on': False}}
        x = self.hsb.copy()
        x['on'] = True if x['bri'] else False
        return {'state': x}

class Bridge(object):
    def __init__(self, ip, secret):
        self.ip = ip
        self.secret = secret
        self.lights = [HLight() for x in range(0,10)]

# Tradfri section
class TLight(object):
    def __init__(self):
        self.color = None
        self.dimmer = None
        self.state = None
        self.has_light_control = True
        self.lights = [self]

    @property
    def hex_color(self):
        return self.color

    @property
    def light_control(self):
        return self

    def set_state(self, state):
        self.state = state

    def set_hex_color(self, color):
        self.color = color

    def set_dimmer(self, dimmer):
        self.dimmer = dimmer

class TAPI(object):
    def __init__(self, ip, secret):
        self.ip = ip
        self.secret = secret

class Gateway(object):
    def __init__(self, api):
        self.api = api
        self.lights = [TLight() for x in range(0,10)]

    def get_devices(self):
        return self.lights

