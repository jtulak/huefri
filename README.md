# Huëfri
A simple software bridge to unify IKEA Trådfri and Philips Hue lights.

Did you thought how nice it would be to control Philips Hue bulbs with IKEA
Trådfri remote, or vice versa? This small bridge makes it possible.

![A short video with one Hue bulb, one Trådfri bulb and one Trådfri remote.](https://raw.githubusercontent.com/jtulak/huefri/master/example.gif)

All operations of the remote are supported: on/off, brightness level, change of
white light temperature. Once the master Trådfri bulb changes its state, the Hue
bulbs are set to the same temperature/brightness and if you change the master Hue bulb,
all configure Trådfri bulbs change its state too.

For the Hue -> Trådfri synchronisation of color, only three specific colors are
supported. If you set up any other, only brightness will be propagated. See
`COLORS_MAP` for those colors (and change them if you want).

In case of Trådfri -> Hue, as long as you use the three default colors, Hue
will be synced. If you manually set some other color, only brightness is
propagated.

## How it works
You press a button on an IKEA remote. The paired Trådfri bulb changes its light
and within one second, all other configured Hue bulbs changes too.

It is far from ideal, but until IKEA provides us with a way how to subscribe to
events on a remote, all we can do is to watch Trådfri bulbs and repeat any
change on other bublbs. The same approach is used also for the opposite way,
       from Hue to Trådfri.

Right now, this project supports only dual 1:N pairing. That means, it can
watch only one Trådfri bulb (and remote) and propagate to N Hue bulbs, and 1
Hue bulb to N Trådfri.

## Required HW
  * Hue bridge
  * Hue bulbs
  * Trådfri gate
  * Trådfri bulbs
  * A remote (Trådfri, Hue, ...)

Note: I have only Color Ambiance Hue bulbs. If White Ambiance bulbs won't work out of box, I will welcome any patch!

## Dependencies
  * Python 3
  * [qhue](https://github.com/quentinsf/qhue)
  * [pytradfri](https://github.com/ggravlingen/pytradfri)

## Instalation
1. Get all HW working on its own.
2. Install dependencies (see the project sites).
3. Create a `config.json` file in the same directory as `huefri.py` is. See bellow for a template.
4. Just run `python3 huefri.py`

## Configuration
This is a template for `config.json` file that has to be located next to `huefri.py`.
~~~~
{
"hue":{
	"addr":"ADDR",
	"secret": "SECRET",
	"controlled": [LIST,OF,HUE,LIGHTS,TO,CONTROL (indexed from 1) ]
	"main": WATCHED HUE BULB (indexed from 1)
	},
"tradfri":{
	"addr": "ADDR",
	"secret": "SECRET",
	"controlled": [LIST,OF,TRADFRI,LIGHTS,TO,CONTROL (indexed from 0) ]
	"main": WATCHED TRADFRI BULB (indexed from 0)
	}
}
~~~~

To get the Hue secret code, you can use for example [phue](https://github.com/studioimaginaire/phue) project:
~~~~
from phue import Bridge

b = Bridge('ip_of_your_bridge')

# Press the button on the bridge and call connect() 
# within 30 seconds (this only needs to be run a single time).
# The secret will be saved into HOME_DIR/.python_hue file.
b.connect()
~~~~

For Tradfri secret code (16 characters long string), peek at the back of your
Tradfri Gateway.

## Use as a library
You can use this project as library too:
~~~~
from huefri.hue import Hue
from huefri.tradfri import Tradfri

# Both objects needs a reference of the other one.
# The ordr doesn't matter.
# Config is loaded automatically from the config file when using autoinit.
hue = Hue.autoinit()
tradfri = Tradfri.autoinit(hue)
hue.set_tradfri(tradfri)

# All lights are at your service. :-)
~~~~

## Development
If you want to submit a pull request, please, test your changes:
`python3 unittests.py`, or/and add relevant new tests.
