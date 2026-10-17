import network
import time
import secrets
import ntptime
import machine

ssid = secrets.wifi_name
password = secrets.wifi_pass

# Use nominal frequency for long-running stability. Overclocking is opt-in.
normal_freq = 125_000_000  # 125 MHz
OVERCLOCK_ENABLED = False
overclock_freq = 250_000_000  # Used only when OVERCLOCK_ENABLED is True.


def set_time():
    print('\nSetting RTC...')
    print("Local time before synchronization: %s" %str(time.localtime()))
    ntptime.settime()
    print("Local time after synchronization: %s" %str(time.localtime()))


def connect():
    print('Scanning for available WiFi networks...')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    for n in wlan.scan():
        print('ssid:', n[0], ' | bssid:', n[1], ' | channel:', n[2], ' | RSSI:', n[3], ' | security:', n[4], ' | hidden:', n[5])
    
    print('\nConnecting to \'', ssid, '\'...')
    wlan.connect(ssid, password)

    max_wait = 20
    while max_wait > 0:
        wlan_status = wlan.status()
        if  wlan_status < 0 or wlan_status >= 3:
            break
        max_wait -= 1
        print('Attemts left: ', max_wait, ' | Wlan status: ', wlan_status, ' | Waiting for connection to ', secrets.wifi_name)
        time.sleep(2)

    if wlan.status() != 3:
        raise RuntimeError('Network connection failed')
    else:
        print('Connected to \'', ssid, '\'')
        status = wlan.ifconfig()
        print('ip = ' + status[0])


def set_cpu_frequency():
    print('Current freq:', machine.freq()/1000000, 'Mhz')

    try:
        machine.freq(overclock_freq if OVERCLOCK_ENABLED else normal_freq)
    except Exception as e:
        machine.freq(normal_freq)
        print('Frequency change failed, setting to nominal frequency:', e)
        
    print('CPU frequency:', machine.freq()/1000000, 'Mhz')


def run():
    set_cpu_frequency()
    try:
        connect()       
        set_time()
    except Exception as e:
        print('Initialization failed:', e)
        print('Continuing with the current RTC; network time is not synchronized.')
        return False
    finally:
        # No network traffic is needed after startup; release Wi-Fi resources.
        try:
            network.WLAN(network.STA_IF).active(False)
        except Exception as e:
            print('Could not disable Wi-Fi:', e)
    return True
