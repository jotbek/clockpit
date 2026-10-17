# Hardware wiring

The diagrams describe a 5 V RGB NeoPixel 16×16 matrix, three normally open momentary buttons, and a latching main power switch. They use the current GPIO assignments in `main.py` and apply to the Pico W and Pico 2 W header layout.

## Diagrams

| Main switch | Vector diagram | Raster diagram |
| --- | --- | --- |
| Standard ON/OFF | [wiring.svg](wiring.svg) | [wiring.png](wiring.png) |
| Four-terminal illuminated ON/OFF | [wiring-illuminated.svg](wiring-illuminated.svg) | [wiring-illuminated.png](wiring-illuminated.png) |

The drawing shows the component side with USB at the top. Numbers next to pads are physical header positions; `GP5`, for example, means GPIO 5, not physical pin 5. Dots mark wire junctions. Crossings without a dot are not connected.

## Firmware connections

| Function | Assignment in `main.py` | Physical pin | Wiring |
| --- | --- | --- | --- |
| Mode | `modeButton = Pin(5, Pin.IN, Pin.PULL_UP)` | 7 | Momentary contact to GND; pin 8 is nearby |
| Up / + | `plusButton = Pin(13, Pin.IN, Pin.PULL_UP)` | 17 | Momentary contact to GND; pin 18 is nearby |
| Down / − | `minusButton = Pin(9, Pin.IN, Pin.PULL_UP)` | 12 | Momentary contact to GND; pin 13 is nearby |
| Matrix data | `ledControlPin = 22` | 29 | GP22 to DIN, not DOUT |
| Pico power | VSYS | 39 | Switched, regulated +5 V |
| Shared ground | GND | 28 | Supply negative, matrix GND and Pico GND |

`handle_buttons()` reads each input with `.value() == 0`. A released input is held high by its internal pull-up; pressing the button connects it to ground. No external pull-up is required. The Mode, Up and Down buttons are momentary controls; S4 is a separate latching power switch and does not use a GPIO.

For a four-leg tactile button, the two legs on one side may already be connected internally. Use contacts that are open when released and connected only when pressed; check continuity without power. Any Pico GND pad can be used instead of the particular ground pads shown.

The direct 3.3 V data connection matches the existing Clockpit build. It assumes the selected matrix accepts the Pico's data-high level while powered from 5 V; this is not guaranteed for every NeoPixel-compatible panel. This documentation does not add a level shifter or external protection diode.

## Power and the main switch

The supply positive goes through S4, then splits into two branches: one to VSYS (physical pin 39), the other directly to the matrix's +5 V input. The supply negative connects to Pico GND and matrix GND. Route the matrix supply current through suitable wires and the switch, rather than through a Pico header power path. Do not feed 5 V into `3V3 OUT` or a GPIO.

Use a regulated 5 V supply with capacity for the actual panel and brightness. Firmware brightness can be raised to 255/255, so the default setting of 96/255 is not a hardware current limit. Check the switch's **DC** current rating and wiring capacity against the maximum intended load. A quoted AC contact rating does not establish the corresponding DC rating.

S4 turns off the complete clock when USB is disconnected. No firmware change is required for either power-switch variant.

## Illuminated four-terminal switch

The illuminated diagram represents a latching contact pair and a separate indicator pair. Its four labels describe electrical functions, **not physical terminal locations or manufacturer pin numbers**. Confirm the contact pair and indicator polarity from the markings or the manufacturer's terminal drawing before wiring. Check the contact pair for continuity with the switch disconnected from all power.

| Function label in diagram | Connection |
| --- | --- |
| IN | Supply +5 V before S4 |
| OUT | Switched +5 V feeding VSYS and the matrix |
| LED + | OUT / switched +5 V |
| LED − | Common GND |

This makes the indicator follow the main switch. Connect the switch's complete indicator assembly, not an unprotected bare LED.

The seller descriptions for **Weber Bi12B** and **BBi12B**, both marketed as 12 mm / 12 V LED switches, specify an indicator voltage range of **3–12 V**. On that specification, 5 V is within the stated range. The descriptions do not provide a verified terminal arrangement or a DC contact rating; the listed maximum contact rating is 2 A at 230 V. Confirm those details on the actual part before using it to carry the full matrix current. A 230 V illuminated variant is a different part and is not covered by this 5 V indicator diagram. [Bi12B seller description](https://allegro.pl/oferta/wlacznik-przycisk-przelacznik-bistabilny-on-off-12mm-12v-led-wandaloodporny-13957317146), [BBi12B seller description](https://allegro.pl/oferta/wlacznik-przycisk-przelacznik-bistabilny-on-off-12mm-12v-led-wandaloodporny-14319684511).

## USB programming without an external diode

Normal operation uses only the external 5 V supply. The Pico has an onboard path from USB VBUS to VSYS, so plugging in powered USB can energize the VSYS net and the matrix even with S4 off. S4 alone does not isolate those two loads.

1. Turn S4 off and unplug USB before changing wiring.
2. Disconnect the branch wire from switched +5 V to VSYS (pin 39). Leave the shared ground connected.
3. Connect USB to program or inspect the Pico. If running the matrix, power it separately through S4 while the VSYS branch remains disconnected.
4. Before restoring the normal wiring, disconnect USB, turn S4 off, and reconnect the VSYS branch.

This avoids tying the external supply and USB power together through VSYS. Raspberry Pi documents direct external VSYS powering when USB is unused, and external diode isolation when combining supplies. See section 3.5 of the [Pico 2 W datasheet](https://datasheets.raspberrypi.com/picow/pico-2-w-datasheet.pdf).

## Pinout references

- [Official Pico 2 W pinout](https://datasheets.raspberrypi.com/picow/pico-2-w-pinout.pdf).
- [Official Pico W pinout](https://datasheets.raspberrypi.com/picow/PicoW-A4-Pinout.pdf).
- [Pico 2 W datasheet: power chain and external supply](https://datasheets.raspberrypi.com/picow/pico-2-w-datasheet.pdf), sections 3.4–3.5.

[Back to README](../README.md)
