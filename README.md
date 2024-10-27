# LED Matrix Display with Raspberry Pi Pico

This project showcases a variety of animations and functionalities on a 16x16 LED matrix using a Raspberry Pi Pico running MicroPython. It includes multiple modules that display different animations, a digital clock with daylight saving time adjustments for Poland, and interactive controls via buttons.

# Features
* Multiple Animations: Includes various visual effects like Fire Plasma, Game of Life, Rainbow, and more.
* Digital Clock: Displays the current time with automatic adjustment for daylight saving time in Poland.
* Interactive Controls: Three buttons allow users to switch between modules and adjust brightness.
* Optimized Performance: Uses overclocking and efficient coding practices for smooth animations.

# Hardware Requirements
* Raspberry Pi Pico: The main microcontroller running MicroPython.
* 16x16 LED Matrix: A matrix of RGB LEDs to display animations. (TODO: add more info)
* Three Buttons: For user interaction—module selection and brightness control.
* Wi-Fi Module (Optional): For time synchronization via NTP (requires Wi-Fi credentials).

# Setup Instructions
1. Clone the Repository:

```bash
git clone https://github.com/yourusername/led-matrix-pico.git
```

2. Prepare the Raspberry Pi Pico:
    * Install MicroPython on your Pico if not already done.
    * Copy all .py files to the Pico's filesystem.

3. Configure Wi-Fi (Optional for Clock Module):
    * Create a ```secrets.py``` file on the Pico with your Wi-Fi credentials:

```python
wifi_name = 'your_ssid'
wifi_pass = 'your_password'
```

4. Wiring:
    * Connect the LED matrix to the Pico according to your matrix's specifications.
    * Connect the three buttons to GPIO pins 5, 9, and 13 with pull-up resistors.

5. Run the Program:
    * Reset the Pico or run main.py to start the program.

# Modules Description
1. Clock (```mod_clock.py```)

    Displays the current time, adjusting automatically for daylight saving time in Poland (CEST/CET). It shows hours and minutes with a seconds indicator around the border.

    * Features:
        * Automatic DST adjustment.
        * Visual seconds indicator.
        * Customizable colors.

2. Fire Plasma (```mod_fireplasma.py```)

    Creates a dynamic fire-like plasma effect using heat maps and color gradients.

    * Features:
        * Realistic fire animation.
        * Configurable fire spawn rate and damping factor.

3. Color Vortex (```mod_vortex.py```)
    Displays a swirling vortex of colors that shifts hues over time, creating a mesmerizing effect.

    * Features:
        * Smooth color transitions.
        * Adjustable rotation speed.

4. Game of Life (```mod_gameoflife.py```)
    Implements Conway's Game of Life with evolving cellular automata patterns.

    * Features:
        * Random initial states.
        * Automatic reset after a set time.

5. Lava (mod_lava.py)
    Simulates a lava lamp effect with flowing, molten colors.

    * Features:
        * Sinusoidal color calculations.
        * Continuous color flow.

6. Fireplace (```mod_fireplace.py```)
    Mimics the appearance of a cozy fireplace with flickering flames.

    * Features:
        * Sparks and embers.
        * Low-pass filtering for smoother visuals.

7. Matrix Rain (```mod_matrixrain.py```)
    Recreates the "digital rain" effect from the Matrix movies.

    * Features:
    * Falling green code streams.
    * Adjustable speed and color intensity.

8. Rainbow (```mod_rainbow.py```)
    Displays a vibrant rainbow that shifts colors across the LED matrix.

    * Features:
        * Hue shifting for dynamic colors.
        * Increased saturation and brightness.

9. Santa Tree (```mod_santatree_16x16.py```)
    Shows a festive Christmas tree with sparkling lights.

    * Features:
        * Predefined tree pattern.
        * Randomly changing sparkles.

# Button Controls

* Mode Button (GPIO 5):
    * Press: Switch between module selection mode and brightness adjustment mode.
    * Indicator: Blinks green for module mode, blue for brightness mode.

* Plus Button (GPIO 13):
    * Module Mode: Switch to the next module.
    * Brightness Mode: Increase brightness.

* Minus Button (GPIO 9):
    * Module Mode: Switch to the previous module.
    * Brightness Mode: Decrease brightness.

# Customization
* Add New Modules:
    * Create a new ```mod_yourmodule.py``` file.
    * Implement a class with a ```get()``` method returning ```(is_full_frame, delay_ms, changes)```.
    * Add your module to the ```modules``` list in ```main.py```.

* Adjust Brightness:
    * Modify the ```intense``` and ```intense_step``` variables in ```main.py``` for default brightness settings.

* Change Wi-Fi Settings:
    * Update the ```secrets.py``` file with new credentials.

* Overclocking:
    * The Pico is overclocked to 250 MHz by default.
    * Adjust ```overclock_freq``` in ```init.py``` if necessary.

# License
This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).