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
import datetime

import dummy
import huefri
import huefri.common
from huefri.hue import Hue
from huefri.common import Config
from huefri.common import DELTA



class TestHue(unittest.TestCase):

    def setUp(self):
        self.fnt_log = huefri.common.log
        huefri.common.log = lambda x,y: None
        huefri.hue.log = lambda x,y: None
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
        with mock.patch('qhue.Bridge', dummy.Bridge) as m:
            self.hue = Hue.autoinit(Config)

    def tearDown(self):
        huefri.common.COLORS_MAP = self.cls_map
        huefri.common.log = self.fnt_log

    def test_init(self):
        with mock.patch('qhue.Bridge', dummy.Bridge) as m:
            hue = Hue.autoinit(Config)
        self.assertEqual('hue', hue.ip)
        self.assertIsNone(hue.hue)
        self.assertIsNone(hue.tradfri)
        self.assertTrue(isinstance(hue.bridge, dummy.Bridge))

    def test__set_hsb_selected(self):
        light = self.hue.bridge.lights[1]
        self.hue._set_hsb_selected(light, {'hue':  7644, 'sat': 150, 'bri': 200})
        self.assertEqual(light.hsb, {'hue':  7644, 'sat': 150, 'bri': 200})

    def test_set_hsb(self):
        self.hue.set_hsb({'hue':  7644, 'sat': 150, 'bri': 100})
        self.assertDictEqual(self.hue.bridge.lights[1].hsb,
                {'hue':  7644, 'sat': 150, 'bri': 100})
        self.assertDictEqual(self.hue.bridge.lights[2].hsb,
                {'hue':  7644, 'sat': 150, 'bri': 100})
        self.assertDictEqual(self.hue.bridge.lights[3].hsb,
                {'hue':  7644, 'sat': 150, 'bri': 100})
        self.assertEqual(1, self.hue.current_color_index)

        # and verify that it didn't try to set up zero index or any other light
        self.assertEqual(self.hue.bridge.lights[4].hsb, None)
        self.assertEqual(self.hue.bridge.lights[0].hsb, None)

    def test_changed(self):
        # exception if we don't know about tradfri
        self.hue.tradfri = None
        with self.assertRaises(Exception):
            self.hue.changed()

        # set up
        self.hue.set_hsb({'hue':  7644, 'sat': 150, 'bri': 100})
        self.hue.tradfri = dummy.DummyHub()

        # save current state
        self.hue.tradfri.set_time_to_now()
        self.assertFalse(self.hue.changed())
        # move time, test if it remembers state
        self.hue.tradfri.set_time_to_past()
        self.assertFalse(self.hue.changed())

        # change state
        self.hue.set_hsb({'hue':  39312, 'sat': 13, 'bri': 100})
        self.assertTrue(self.hue.changed())
        # move time, test if it remembers state
        self.hue.tradfri.set_time_to_past()
        self.assertFalse(self.hue.changed())


    def test_update(self):
        self.hue.tradfri = dummy.DummyHub()

        # the colors of tradfri should change
        with mock.patch('huefri.hue.Hue.changed', lambda x: True) as m:
            self.hue.set_hsb({'hue':  7644, 'sat': 150, 'bri': 100})
            self.hue.update()
            self.assertEqual("f1e0b5", self.hue.tradfri.rgb)
            self.assertEqual(100, self.hue.tradfri.bri)

        # the colors of tradfri should stay same as in the previous case
        with mock.patch('huefri.hue.Hue.changed', lambda x: False) as m:
            self.hue.set_hsb({'hue': 39312, 'sat':  13, 'bri': 150})
            self.hue.update()
            self.assertEqual("f1e0b5", self.hue.tradfri.rgb)
            self.assertEqual(100, self.hue.tradfri.bri)

