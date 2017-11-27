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

import huefri
from huefri.common import Config as Config
from huefri.common import HuefriException as HuefriException
from huefri.common import log as log
from huefri.hue import Hue as Hue
from huefri.tradfri import Tradfri as Tradfri

def main():
    initialized = False
    """
        Forever check the main light and update Hue lights.
    """
    try:
        while True:
            try:
                if not initialized:
                    hue = Hue.autoinit()
                    tradfri = Tradfri.autoinit(hue)
                    hue.set_tradfri(tradfri)
                    initialized = True
                else:
                    tradfri.update()
                    hue.update()
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

