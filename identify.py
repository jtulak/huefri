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
import time
import os
import sys
import datetime
import traceback
import huefri
from huefri.common import log
from huefri.common import Config
from huefri.tradfri import Tradfri

class TradfriBlink(Tradfri):
    """ A tradfri class extended by a blinking method. """

    def blink(self, step, index):
        """ Blink, one change per step. """
        state = True
        # blink on odd numbers
        if step % 2:
            state = False

        done = False
        while not done:
            try:
                if state:
                    self._set(index, "f1e0b5", 254)
                    done = True
                else:
                    self._set(index, "f1e0b5", 50)
                    done = True
            except pytradfri.error.RequestTimeout:
                """ This exception is raised here and there and doesn't cause anything.
                    So print just a short notice, not a full stacktrace.
                """
                log("MAIN", "Tradfri request timeout, retrying...")

def main():
    initialized = False
    Config.path = os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    "config.json")
    try:
        while True:
            try:
                if not initialized:
                    tradfri = TradfriBlink.autoinit(Config)
                    initialized = True
                else:
                    for i,light in enumerate(tradfri._lights):
                        print("blinking light %d" % i)
                        step = 0
                        for x in range(7):
                            tradfri.blink(step, i)
                            step += 1
                            time.sleep(1)

            except pytradfri.error.ClientError as e:
                print("An error occured with Tradfri: %s" % str(e))
            except pytradfri.error.RequestTimeout:
                """ This exception is raised here and there and doesn't cause anything.
                    So print just a short notice, not a full stacktrace.
                """
                log("MAIN", "Tradfri request timeout, retrying...")
            except Exception as err:
                traceback.print_exc()
                log("MAIN", err)
            time.sleep(1)
    except KeyboardInterrupt:
        log("MAIN", "Exiting on ^c.")
        sys.exit(0)

if __name__ == '__main__':
    main()

