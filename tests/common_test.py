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
from unittest import mock as mock
import json
import huefri
import huefri.common



class TestConfig(unittest.TestCase):

    def setUp(self):
        self.fnt_log = huefri.common.log
        huefri.common.log = lambda x,y: None

    def tearDown(self):
        huefri.common.log = self.fnt_log


    def test_bad_path(self):
        with self.assertRaises(huefri.common.BadConfigPathError):
            huefri.common.Config.path = "foobar"
            huefri.common.Config.get()

    def test_bad_content(self):
        with self.assertRaises(json.decoder.JSONDecodeError):
            with mock.patch('huefri.common.open', mock.mock_open(read_data='bibble')) as m:
                huefri.common.Config.path = "foobar"
                huefri.common.Config.get()

    def test_good_file(self):
        config="""{
        "hue":{
            "addr":"hue",
            "secret": "SECRET1",
            "controlled": [1,2,3],
            "main": 1
            },
        "tradfri":{
            "addr": "tradfri",
            "secret": "SECRET2",
            "controlled": [0],
            "main": 0
            }
        }"""
        with mock.patch('huefri.common.open', mock.mock_open(read_data=config)) as m:
            huefri.common.Config.path = "foobar"
            huefri.common.Config.get()
            self.assertEqual("hue", huefri.common.Config.get()['hue']['addr'])
            self.assertEqual("SECRET2", huefri.common.Config.get()['tradfri']['secret'])

class TestColors(unittest.TestCase):

    def setUp(self):
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

    def tearDown(self):
        huefri.common.COLORS_MAP = self.cls_map


    def test_hsb2hex(self):
        self.assertEqual("f1e0b5", huefri.common.hsb2hex(7644, 150))
        self.assertEqual("f5faf6", huefri.common.hsb2hex(39312, 13))

    def test_hex2hsb(self):
        self.assertEqual({'on': True, 'hue':  6188, 'sat': 249, 'bri': '150'},
                huefri.common.hex2hsb("efd275", "150"))
        self.assertEqual({'on': True, 'hue':  7644, 'sat': 150, 'bri': '150'},
                huefri.common.hex2hsb("f1e0b5", "150"))
