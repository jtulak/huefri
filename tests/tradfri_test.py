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

import unittest
from unittest import mock
import json
import dummy
import huefri
import huefri.common
from huefri.common import Config
from huefri.tradfri import Tradfri
from random import shuffle



class TestTradfri(unittest.TestCase):

    def setUp(self):
        self.fnt_log = huefri.common.log
        huefri.common.log = lambda x,y: None
        huefri.tradfri.log = lambda x,y: None
        huefri.common.Config._state = json.loads("""{
            "hue":{
                "addr":"hue",
                "secret": "SECRET1",
                "controlled": [1,2,3],
                "main": 1
                },
            "tradfri":{
                "addr": "tradfri",
                "secret": "SECRET2",
                "controlled": [0,1,2],
                "main": 0
                }
            }""")
        self.map = [
            {"hex": "efd275", # warm - 34,98 in OpenHab
                "hsb": {'on': True, 'hue':  6188, 'sat': 249}},
            {"hex": "f1e0b5", # medium - 42,59 in OpenHab
                "hsb": {'on': True, 'hue':  7644, 'sat': 150}},
            {"hex": "f5faf6", # cold - 216,5 in OpenHab
                "hsb": {'on': True, 'hue': 39312, 'sat':  13}},
        ]
        self.cls_map = huefri.common.COLORS_MAP
        huefri.common.COLORS_MAP = self.map
        with mock.patch('huefri.tradfri.APIFactory', dummy.TAPIFactory) as m:
            with mock.patch('huefri.tradfri.Gateway', dummy.Gateway) as n:
                self.tradfri = Tradfri.autoinit(Config)
                self.tradfri.gateway.api = self.tradfri.api

    def tearDown(self):
        huefri.common.log = self.fnt_log
        huefri.common.COLORS_MAP = self.cls_map

    def test_init(self):
        with mock.patch('huefri.tradfri.APIFactory', dummy.TAPIFactory) as m:
            with mock.patch('huefri.tradfri.Gateway', dummy.Gateway) as n:
                tradfri = Tradfri.autoinit(Config)
        self.assertEqual('tradfri', tradfri.api.ip)
        self.assertIsNone(tradfri.color)
        self.assertTrue(isinstance(tradfri.gateway, dummy.Gateway))

    def test__set(self):
        self.tradfri._set(0, "caffee", 100)
        self.assertEqual("caffee", self.tradfri.gateway.lights[0].color)
        self.assertEqual(100, self.tradfri.gateway.lights[0].dimmer)
        self.assertTrue(self.tradfri.gateway.lights[0].state)

        self.tradfri._set(0, "caffee", 0)
        self.assertEqual("caffee", self.tradfri.gateway.lights[0].color)
        self.assertFalse(self.tradfri.gateway.lights[0].state)

        # we didn't changed any other light
        self.assertIsNone(self.tradfri.gateway.lights[1].color)

    def test_set_all(self):
        self.tradfri.set_all("efd275", 150)
        self.assertEqual("efd275", self.tradfri.gateway.lights[0].color)
        self.assertEqual("efd275", self.tradfri.gateway.lights[1].color)
        self.assertEqual("efd275", self.tradfri.gateway.lights[2].color)
        self.assertIsNone(self.tradfri.gateway.lights[3].color)
        self.assertEqual(0, self.tradfri.current_color_index)

        self.assertEqual(150, self.tradfri.gateway.lights[0].dimmer)
        self.assertTrue(self.tradfri.gateway.lights[2].state)

    def test_changed(self):
        # exception if we don't know about hue
        self.tradfri.hue = None
        with self.assertRaises(Exception):
            self.tradfri.changed()

        # set up
        self.tradfri.set_all("f1e0b5", 150)
        self.tradfri.hue = dummy.DummyHub()

        # save current state
        self.tradfri.hue.set_time_to_now()
        self.assertFalse(self.tradfri.changed())
        # move time, test if it remembers state
        self.tradfri.hue.set_time_to_past()
        self.assertFalse(self.tradfri.changed())

        # change state
        self.tradfri.set_all("f5faf6", 100)
        self.assertTrue(self.tradfri.changed())
        # move time, test if it remembers state
        self.tradfri.hue.set_time_to_past()
        self.assertFalse(self.tradfri.changed())


    def test_update(self):
        self.tradfri.hue = dummy.DummyHub()

        # the colors of tradfri should change
        with mock.patch('huefri.tradfri.Tradfri.changed', lambda x: True) as m:
            self.tradfri.set_all("efd275", 100)
            self.tradfri.update()
            self.assertEqual({'on': True, 'hue':  6188, 'sat': 249, 'bri': 100}, self.tradfri.hue.hsb)

        # the colors of tradfri should stay same as in the previous case
        with mock.patch('huefri.tradfri.Tradfri.changed', lambda x: False) as m:
            self.tradfri.set_all("f5faf6", 150)
            self.tradfri.update()
            self.assertEqual({'on': True, 'hue':  6188, 'sat': 249, 'bri': 100}, self.tradfri.hue.hsb)

    def test_sort_by_name(self):
        # sorted... probably works, because the dummy lights are in order
        names = [l.name for l in self.tradfri._lights]
        self.assertEqual([str(x) for x in range(10)], names)
        # randomize the order and try again
        shuffle(self.tradfri.api.lights)
        names = [l.name for l in self.tradfri._lights]
        self.assertEqual([str(x) for x in range(10)], names)

