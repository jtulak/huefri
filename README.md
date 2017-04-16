# huefri
A simple bridge to unify IKEA Tradfri and Philips Hue lights.

Did you thought how nice it would be to control Philips Hue bulbs with IKEA Tradfri remote? This small bridge makes it possible.

## How it works
You press a button on an IKEA remote. The paired Tradfri bulb changes its light and within one second, all other configured Hue bulbs changes too.

It is far from ideal, but until IKEA provides us with a way how to subscribe to events on a conremote, all we can do is to watch Tradfri bulbs and repeat any change on other bublbs.

Right now, this project supports only 1:N pairing. That means, it can watch only one Tradfri bulb (and remote) and propagate to N Hue bulbs. I don't need other Tradfri light right now, so I can't test/develop any other configuration. I'm happy to accept patches, though.

## Required HW
  * Hue bridge
  * Tradfri gate
  * One Tradfri bulb and a remote
  * Any number of Hue bulbs

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
	},
"tradfri":{
	"addr": "ADDR",
	"secret": "SECRET",
	"main": WATCHED TRADFRI BULB (indexed from 0)
	}
}
~~~~

To get the Hue secret code, you can use for example [phue](https://github.com/studioimaginaire/phue) project:
~~~~
from phue import Bridge

b = Bridge('ip_of_your_bridge')

# Press the button on the bridge and call connect() within 30 seconds (this only needs to be run a single time)
# The secret will be saved into /Users/Honza/.python_hue file.
b.connect()
~~~~

## TODO
  * Add possibility to control other Tradfri bulbs too, to simulate multiple remotes on a single group of lights, something IKEA can't do yet.

