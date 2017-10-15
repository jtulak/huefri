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
import dummy
import huefri
import huefri.common
from huefri.tradfri import Tradfri



class TestTradfri(unittest.TestCase):

    def setUp(self):
        self.fnt_log = huefri.common.log
        huefri.common.log = lambda x,y: None
        huefri.common.Config._config = json.loads("""{
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
        with mock.patch('pytradfri.coap_cli.api_factory', dummy.TAPI) as m:
            with mock.patch('pytradfri.gateway.Gateway', dummy.Gateway) as n:
                self.tradfri = Tradfri.autoinit()

    def tearDown(self):
        huefri.common.log = self.fnt_log

    def test_init(self):
        with mock.patch('pytradfri.coap_cli.api_factory', dummy.TAPI) as m:
            with mock.patch('pytradfri.gateway.Gateway', dummy.Gateway) as n:
                tradfri = Tradfri.autoinit()
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
        self.tradfri.set_all("bababa", 150)
        self.assertEqual("bababa", self.tradfri.gateway.lights[0].color)
        self.assertEqual("bababa", self.tradfri.gateway.lights[1].color)
        self.assertEqual("bababa", self.tradfri.gateway.lights[2].color)
        self.assertIsNone(self.tradfri.gateway.lights[3].color)

        self.assertEqual(150, self.tradfri.gateway.lights[0].dimmer)
        self.assertTrue(self.tradfri.gateway.lights[2].state)

