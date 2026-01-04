import threading

import evdev
import sys
from evdev import ecodes, AbsInfo
from evdev import ecodes, AbsInfo, AbsEvent
from evdev.ecodes import BTN_MISC

devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

if not devices:
    print('No evdev devices found on your system.',
          'Check your evdev installation and device permissions.')
    sys.exit(1)

namemap = {}
for d in devices:
    namemap[d.name] = d.path

if len(sys.argv) != 2 or sys.argv[1] not in namemap.keys():
    print("Please specify device to spoof.")
    print("Available devices:")
    for d in namemap.keys():
        print(d)
    sys.exit(1)

device = None
for d in devices:
    if d.name == sys.argv[1] or d.path == sys.argv[1]:
        device = d
        break

if not device:
    print('Device', sys.argv[1], 'not found')
    sys.exit(1)

print("Using:", device.name)

caps = { #this won't work: device.capabilities()
    ecodes.EV_MSC : [ecodes.MSC_SCAN]
}

caps[ecodes.EV_KEY] = [ #caps for key codes we send. refer to map below!
    ecodes.BTN_JOYSTICK, ecodes.BTN_TRIGGER, BTN_MISC,
    ecodes.BTN_0, ecodes.BTN_1, ecodes.BTN_2, ecodes.BTN_3,
    ecodes.BTN_4, ecodes.BTN_5, ecodes.BTN_6, ecodes.BTN_7, ecodes.BTN_8, ecodes.BTN_9,
    ecodes.BTN_X, ecodes.BTN_Y, #ecodes.BTN_A
]

eventLUT = { #this maps incoming events to outgoing events by changing their code.
    ecodes.REL_X: ecodes.ABS_X,
    ecodes.REL_Y: ecodes.ABS_Y,
    ecodes.REL_Z: ecodes.ABS_Z,
    ecodes.REL_RX: ecodes.ABS_RX,
    ecodes.REL_RY: ecodes.ABS_RY,
    ecodes.REL_RZ: ecodes.ABS_RZ,

    282: ecodes.BTN_JOYSTICK,

    268: ecodes.BTN_0, #1
    269: ecodes.BTN_1, #2
    270: ecodes.BTN_2, #3
    271: ecodes.BTN_3, #4

    278: ecodes.BTN_4, #5
    280: ecodes.BTN_5, #6
    281: ecodes.BTN_6, #7
    279: ecodes.BTN_7, #8

    256: ecodes.BTN_A, #A?
    257: ecodes.BTN_JOYSTICK, #B?

    264: ecodes.BTN_8, #9
    258: ecodes.BTN_Y, #?
    261: ecodes.BTN_9, #10
    260: ecodes.BTN_X #?
}

if not ecodes.EV_ABS in device.capabilities():
    # 3d space mouse reports only relative axes, so we need to set up absolute ones
    axisInfo = AbsInfo(value=0, min=-32768, max=32768, fuzz=1024, flat=8192, resolution=0)
    caps[ecodes.EV_ABS] = [
        (ecodes.ABS_X, axisInfo),
        (ecodes.ABS_Y, axisInfo),
        (ecodes.ABS_Z, axisInfo),
        (ecodes.ABS_RX, axisInfo),
        (ecodes.ABS_RY, axisInfo),
        (ecodes.ABS_RZ, axisInfo)
    ]

try:
    spoofdevice = evdev.uinput.UInput(events=caps,
                                     name=d.name + " Joystick",
                                     vendor=0xdead, #device.info.vendor,
                                     product=0xbeef, #device.info.product,
                                     version=device.info.version)
except Exception as e:
    print('Failed to create UInput:', e)
    sys.exit(1)

print("Spoofing:", spoofdevice)
print("Mirroring events...")

for event in device.read_loop():
    #print(event)
    if event.type == ecodes.EV_REL:
        event.type = ecodes.EV_ABS
        event.code = eventLUT[event.code]
        #event.value = event.value + 350
        val = int((1 if event.value >= 0 else -1) * ((abs(event.value) / 350.0) ** 2) * 32678)
        event.value = val
    if event.type == ecodes.EV_KEY:
        event.code = eventLUT[event.code] if event.code in eventLUT else event.code

    spoofdevice.write_event(event)
    spoofdevice.syn()