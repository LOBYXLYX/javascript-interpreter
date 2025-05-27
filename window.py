import math
import json
import queue
import re
import os
import sys
import types
import time
import uuid
import numpy
import hashlib
import random
import threading
import urllib.parse

import quickjs
from uaparser import UAParser
from base64 import b64encode, b64decode
from document import Document, Event, MouseEvent
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_active_intervals = {}
_active_timeouts = {}
_blobs = {}

def _createClass(name):
    return type(name, (object,), {
        '__init__': lambda self: None
    })
    
def _user_agent_data(ua):
    info = UAParser(ua)
    
    return {
        'bw': info.browser['name'],
        'version': info.browser['major'],
        'os': info.os
    }

LANGUAGE = 'es-ES'
SCREEM_RESOLUTIONS = (
    (3440,1440,3440,1400),
    (1924,1007,1924,1007),
    (1920,1080,1920,1040),
    (1280,720,1280,672),
    (1920,1080,1920,1032),
    (1366,651,1366,651),
    (1366,768,1366,738),
    (1920,1080,1920,1050)
)

startE = int(time.time() * 1000)
CHROME_DATA = {
    "app": {
        "InstallState": {
            "DISABLED": "disabled",
            "INSTALLED": "installed",
            "NOT_INSTALLED": "not_installed",
        },
        "RunningState": {
            "CANNOT_RUN": "cannot_run",
            "READY_TO_RUN": "ready_to_run",
            "RUNNING": "running",
        },
        "getDetails": lambda: "[native code]",
        "getIsInstalled": lambda: "[native code]",
        "installState": lambda: "[native code]",
        "isInstalled": False,
        "runningState": lambda: "[native code]",
    },
    "runtime": {
        "OnInstalledReason": {
            "CHROME_UPDATE": "chrome_update",
            "INSTALL": "install",
            "SHARED_MODULE_UPDATE": "shared_module_update",
            "UPDATE": "update",
        },
        "OnRestartRequiredReason": {
            "APP_UPDATE": "app_update",
            "OS_UPDATE": "os_update",
            "PERIODIC": "periodic",
        },
        "PlatformArch": {
            "ARM": "arm",
            "ARM64": "arm64",
            "MIPS": "mips",
            "MIPS64": "mips64",
            "X86_32": "x86-32",
            "X86_64": "x86-64",
        },
        "PlatformNaclArch": {
            "ARM": "arm",
            "MIPS": "mips",
            "MIPS64": "mips64",
            "X86_32": "x86-32",
            "X86_64": "x86-64",
        },
        "PlatformOs": {
            "ANDROID": "android",
            "CROS": "cros",
            "FUCHSIA": "fuchsia",
            "LINUX": "linux",
            "MAC": "mac",
            "OPENBSD": "openbsd",
            "WIN": "win",
        },
        "RequestUpdateCheckStatus": {
            "NO_UPDATE": "no_update",
            "THROTTLED": "throttled",
            "UPDATE_AVAILABLE": "update_available",
        },
        "connect": lambda: "[native code]",
        "sendMessage": lambda: "[native code]",
        "id": None,
    },
    "csi": lambda: {
        "startE": startE,
        "onloadT": startE + 281,
        "pageT": 3947.235,
        "tran": 15,
    },
    "loadTimes": lambda: {
        "requestTime": startE / 1000,
        "startLoadTime": startE / 1000,
        "commitLoadTime": startE / 1000 + 0.324,
        "finishDocumentLoadTime": startE / 1000 + 0.498,
        "finishLoadTime": startE / 1000 + 0.534,
        "firstPaintTime": startE / 1000 + 0.437,
        "firstPaintAfterLoadTime": 0,
        "navigationType": "Other",
        "wasFetchedViaSpdy": True,
        "wasNpnNegotiated": True,
        "npnNegotiatedProtocol": "h3",
        "wasAlternateProtocolAvailable": False,
        "connectionInfo": "h3",
    },
}

WINDOW_EVENT_HANDLERS = {
    "onabort": None,
    "onafterprint": None,
    "onanimationend": None,
    "onanimationiteration": None,
    "onanimationstart": None,
    "onappinstalled": None,
    "onauxclick": None,
    "onbeforeinput": None,
    "onbeforeinstallprompt": None,
    "onbeforematch": None,
    "onbeforeprint": None,
    "onbeforetoggle": None,
    "onbeforeunload": None,
    "onbeforexrselect": None,
    "onblur": None,
    "oncancel": None,
    "oncanplay": None,
    "oncanplaythrough": None,
    "onchange": None,
    "onclick": None,
    "onclose": None,
    "oncommand": None,
    "oncontentvisibilityautostatechange": None,
    "oncontextlost": None,
    "oncontextmenu": None,
    "oncontextrestored": None,
    "oncuechange": None,
    "ondblclick": None,
    "ondevicemotion": None,
    "ondeviceorientation": None,
    "ondeviceorientationabsolute": None,
    "ondrag": None,
    "ondragend": None,
    "ondragenter": None,
    "ondragleave": None,
    "ondragover": None,
    "ondragstart": None,
    "ondrop": None,
    "ondurationchange": None,
    "onemptied": None,
    "onended": None,
    "onerror": None,
    "onfocus": None,
    "onformdata": None,
    "ongotpointercapture": None,
    "onhashchange": None,
    "oninput": None,
    "oninvalid": None,
    "onkeydown": None,
    "onkeypress": None,
    "onkeyup": None,
    "onlanguagechange": None,
    "onload": None,
    "onloadeddata": None,
    "onloadedmetadata": None,
    "onloadstart": None,
    "onlostpointercapture": None,
    "onmessage": None,
    "onmessageerror": None,
    "onmousedown": None,
    "onmouseenter": None,
    "onmouseleave": None,
    "onmousemove": None,
    "onmouseout": None,
    "onmouseover": None,
    "onmouseup": None,
    "onmousewheel": None,
    "onoffline": None,
    "ononline": None,
    "onpagehide": None,
    "onpagereveal": None,
    "onpageshow": None,
    "onpageswap": None,
    "onpause": None,
    "onplay": None,
    "onplaying": None,
    "onpointercancel": None,
    "onpointerdown": None,
    "onpointerenter": None,
    "onpointerleave": None,
    "onpointermove": None,
    "onpointerout": None,
    "onpointerover": None,
    "onpointerrawupdate": None,
    "onpointerup": None,
    "onpopstate": None,
    "onprogress": None,
    "onratechange": None,
    "onrejectionhandled": None,
    "onreset": None,
    "onresize": None,
    "onscroll": None,
    "onscrollend": None,
    "onscrollsnapchange": None,
    "onscrollsnapchanging": None,
    "onsearch": None,
    "onsecuritypolicyviolation": None,
    "onseeked": None,
    "onseeking": None,
    "onselect": None,
    "onselectionchange": None,
    "onselectstart": None,
    "onslotchange": None,
    "onstalled": None,
    "onstorage": None,
    "onsubmit": None,
    "onsuspend": None,
    "ontimeupdate": None,
    "ontoggle": None,
    "ontransitioncancel": None,
    "ontransitionend": None,
    "ontransitionrun": None,
    "ontransitionstart": None,
    "onunhandledrejection": None,
    "onunload": None,
    "onvolumechange": None,
    "onwaiting": None,
    "onwebkitanimationend": None,
    "onwebkitanimationiteration": None,
    "onwebkitanimationstart": None,
    "onwebkittransitionend": None,
    "onwheel": None
}
        
Bluetooth = _createClass('Bluetooth')
Clipboard = _createClass('Clipboard')
CredentialsContainer = _createClass('CredentialsContainer')
Geolocation = _createClass('Geolocation')
Ink = _createClass('Ink')
LockManager = _createClass('LockManager')
MediaCapabilities = _createClass('MediaCapabilities')
Permissions = _createClass('Permissions')
Scheduling = _createClass('Scheduling')
StorageManager = _createClass('StorageManager')
StorageBucketManager = _createClass('StorageBucketManager')
WakeLock = _createClass('WakeLock')
DeprecatedStorageQuota = _createClass('DeprecatedStorageQuota')
IDBFactory = _createClass('IDBFactory')

MimeTypeArray = {
    '0': '',
    '1': '',
    'application/pdf': None
}

PluginArray = {
    '0': '',
    '1': '',
    '2': '',
    'JavaScript Portable Document Format Plugin': None
}

class ObjectPrototypeCall:
    def array_prototype():
        return {
            'length': lambda arr: len(arr),
            'push': lambda arr, *items: (arr.extend(items), len(arr))[1],
            'pop': lambda arr: arr.pop() if arr else None,
            'shift': lambda arr: arr.pop(0) if arr else None,
            'unshift': lambda arr, *items: (arr.__setitem__(slice(0, 0), items), len(arr))[1],
            'join': lambda arr, sep=',': sep.join(map(str, arr)),
            'reverse': lambda arr: arr.reverse() or arr,
            'sort': lambda arr, key=None, reverse=False: (arr.sort(key=key, reverse=reverse), arr)[1],
            'slice': lambda arr, start, end=None: arr[start:end],
            'splice': lambda arr, start, delete_count=None, *items: (
                lambda deleted: (arr.__setitem__(slice(start, start + delete_count), items), deleted)[1]
                if delete_count is not None else arr.__setitem__(slice(start, len(arr)), items)
            )(arr[start:start + delete_count] if delete_count is not None else []),
            'concat': lambda arr, *args: arr + [item for sublist in args for item in (sublist if isinstance(sublist, list) else [sublist])],
            'indexOf': lambda arr, item, start=0: arr.index(item, start) if item in arr[start:] else -1,
            'includes': lambda arr, item: item in arr,
            'forEach': lambda arr, callback: [callback(el, i, arr) for i, el in enumerate(arr)],
            'map': lambda arr, callback: [callback(el, i, arr) for i, el in enumerate(arr)],
            'filter': lambda arr, callback: [el for i, el in enumerate(arr) if callback(el, i, arr)],
            'reduce': lambda arr, callback, initial=None: (
                lambda acc: [acc := callback(acc, el, i, arr) for i, el in enumerate(arr)][-1] if arr else initial
            )(initial if initial is not None else arr[0]),
            'every': lambda arr, callback: all(callback(el, i, arr) for i, el in enumerate(arr)),
            'some': lambda arr, callback: any(callback(el, i, arr) for i, el in enumerate(arr)),
            'find': lambda arr, callback: next((el for i, el in enumerate(arr) if callback(el, i, arr)), None),
            'findIndex': lambda arr, callback: next((i for i, el in enumerate(arr) if callback(el, i, arr)), -1),
            'toString': lambda arr: ','.join(map(str, arr)),
            'valueOf': lambda arr: arr,
            'at': lambda arr, index: arr[index] if -len(arr) <= index < len(arr) else None,
            'fill': lambda arr, value, start=0, end=None: (
                [arr.__setitem__(i, value) for i in range(start, end if end is not None else len(arr))], arr
            )[1],
            'copyWithin': lambda arr, target, start=0, end=None: (
                lambda sub: [arr.__setitem__(target + i, sub[i]) for i in range(len(sub)) if target + i < len(arr)],
                arr
            )[1] if (sub := arr[start:end]) else arr,
            'entries': lambda arr: enumerate(arr),
            'keys': lambda arr: range(len(arr)),
            'values': lambda arr: iter(arr),
        }
    
    def string_prototype():
        def to_py_str(val):
            return str(val) if val is not None else ""

        return {
            'constructor': '',
            'length': lambda s: len(s),
            'charAt': lambda s, i: s[i] if 0 <= i < len(s) else '',
            'charCodeAt': lambda s, i: ord(s[i]) if 0 <= i < len(s) else None,
            'includes': lambda s, substr, start=0: substr in s[start:],
            'indexOf': lambda s, substr, start=0: s.find(substr, start),
            'lastIndexOf': lambda s, substr: s.rfind(substr),
            'startsWith': lambda s, substr, start=0: s.startswith(substr, start),
            'endsWith': lambda s, substr, length=None: s[:length].endswith(substr) if length else s.endswith(substr),
            'slice': lambda s, start, end=None: s[start:end],
            'substring': lambda s, start, end=None: s[min(start, end or len(s)):max(start, end or len(s))],
            'substr': lambda s, start, length=None: s[start:start+length] if length is not None else s[start:],
            'toLowerCase': lambda s: s.lower(),
            'toUpperCase': lambda s: s.upper(),
            'trim': lambda s: s.strip(),
            'repeat': lambda s, count: s * count,
            'padStart': lambda s, targetLength, padString=' ': s.rjust(targetLength, padString),
            'padEnd': lambda s, targetLength, padString=' ': s.ljust(targetLength, padString),
            'split': lambda s, sep=None, limit=None: (s.split(sep) if sep is not None else list(s))[:limit] if limit else (s.split(sep) if sep is not None else list(s)),
            'replace': lambda s, pattern, repl: re.sub(pattern, repl, s, count=1),
            'replaceAll': lambda s, pattern, repl: re.sub(pattern, repl, s),
            'match': lambda s, pattern: re.findall(pattern, s),
            'search': lambda s, pattern: (m := re.search(pattern, s)).start() if m else -1,
            'concat': lambda s, *args: s + ''.join(to_py_str(a) for a in args),
            'toString': lambda s: s,
            'valueOf': lambda s: s,
            'join': lambda s, sep: s.join(sep)
        }
        
    def object_prototype():
        def _is_prototype_of(proto, obj, this=None):
            current = obj['__proto__']
            while current is not None:
                if current is proto:
                    return True
                current = current['__proto__']
            return False
        
        return {
            'hasOwnProperty': lambda obj, prop, this=None: prop in obj,
            'isPrototypeOf': _is_prototype_of,
            'toString': lambda obj=None, this=None: f'[object {obj.get("__class__", "Object")}]',
            'valueOf': lambda obj=None, this=None: obj
        }
        
class JSFunction:
    def __init__(self, func):
        self.func = func
        self.props = {}
        
    def __call__(self, *args, **kwds):
        self.func(*args, **kwds)

    def call(self, this, *args, **kwargs):
        return self.func(this, *args, **kwargs)
    
    def __getitem__(self, key):
        if key in dir(self):
            return getattr(self, key)
        
    def __setitem__(self, key, value):
        self.props[key] = value
        
class JSPropertyFunc:
    def __init__(self, func):
        self.func = func
        
    def __call__(self, *args, **kwds):
        self.func(*args, **kwds)
        
    def bind(self):
        pass
    

class DOMStringList:
    def __init__(self):
        self.length = 0
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func

class Location:
    def __init__(self, domain):
        self.ancestorOrigins = DOMStringList()
        self.hash = ''
        self.host = domain.split('/')[2] if len(domain.split('/')) > 3 else domain
        self.hostName = domain.split('/')[2] if len(domain.split('/')) > 3 else domain
        self.href = ''
        self.origin = 'https://' + domain.split('/')[2] if len(domain.split('/')) > 3 else domain
        self.pathname = domain.split('//')[1].split('/', 1)[1]
        
        if domain.count(':') == 2:
            self.port = domain.split('/', 1)[1].split(':')[1].split('/')[0]
        else:
            self.port = ''
        
        self.protocol = domain.split('//')[0]
        self.search = ''
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
    
class DevicePosture:
    def __init__(self):
        self.onchange = None
        self.type = 'continuous'
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class WGSLLanguageFeatures:
    def __init__(self):
        self.size = 4
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class GPU:
    def __init__(self):
        self.wgslLanguageFeatures = WGSLLanguageFeatures()
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class HID:
    def __init__(self):
        self.onconnect = None
        self.ondisconnect = None
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class NavigatorManagedData:
    def __init__(self):
        self.onmanagedconfigurationchange = None
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class MediaDevices:
    def __init__(self):
        self.ondevicechange = None
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class MediaSession:
    def __init__(self):
        self.metadata = None
        self.playbackState = None
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class Presentation:
    def __init__(self):
        self.defaultRequest = None
        self.receiver = None
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class Serial:
    def __init__(self):
        self.onconnect = None
        self.ondisconnect = None
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class ServiceWorkerContainer:
    def __init__(self):
        self.controller = None
        self.oncontrollerchange = None
        self.onmessage = None
        self.messageerror = None
        self.ready = lambda: {}
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class USB:
    def __init__(self):
        self.onconnect = None
        self.ondisconnect = None
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class UserActivation:
    def __init__(self):
        self.hasBeenActive = True
        self.isActive = False
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class DOMRect:
    def __init__(self):
        self.button = 0
        self.height = 0
        self.left = 0
        self.right = 0
        self.top = 0
        self.width = 0
        self.x = 0
        self.y = 0
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class VirtualKeyboard:
    def __init__(self):
        self.boundingRect = DOMRect()
        self.ongeometrychange = None
        self.overlaysContent = False
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func

class WindowControlsOverlay:
    def __init__(self):
        self.ongeometrychange = None
        self.visible = False
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class XRSystem:
    def __init__(self):
        self.ondevicechange = None
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class NavigatorUAData:
    def __init__(self, user_agent):
        ua_info = _user_agent_data(user_agent)
        
        self.brands = [
            {'brand': ua_info['bw'], 'version': ua_info['version']},
            {'brand': 'Chrome', 'version': ua_info['version']},
            {'brand': 'Not.A/Brand', 'version': '99'}
        ]
        self.mobile = False if 'Android' not in ua_info['os']['name'] else True
        self.platform = ua_info['os']['name']
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class ScreenOrientation:
    def __init__(self):
        self.angle = 0
        self.type = 'landscape-primary'
        self.onchange = None
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func

class Screen:
    def __init__(self):
        o_height, o_width, i_height, i_width = random.choice(list(SCREEM_RESOLUTIONS))
        self.availHeight = o_height
        self.availLeft = 0
        self.availTop = 0
        self.availWidth = o_width
        self.colorDepth = 24
        self.height = o_height
        self.isExtended = False
        self.onchange = None
        self.orientation = ScreenOrientation()
        self.pixelDepth = 24
        self.width = 2560
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
    
class Navigator:
    def __init__(self, user_agent):
        self.appCodeName = 'Mozilla'
        self.appName = 'Netscape'
        self.appVersion = user_agent.lstrip('Mozilla/')
        self.bluetooth = Bluetooth()
        self.clipboard = Clipboard()
        self.cookieEnabled = True
        self.credentials = CredentialsContainer()
        self.deviceMemory = random.randint(1, 3) << 3
        self.devicePosture = DevicePosture()
        self.doNotTrack = None
        self.geolocation = Geolocation()
        self.globalPrivacyControl = True
        self.gpu = GPU()
        self.hardwareConcurrency = random.randint(2, 6)
        self.hid = HID()
        self.ink = Ink()
        self.keyboard = None
        self.language = LANGUAGE
        self.languages = [LANGUAGE]
        self.locks = LockManager()
        self.managed = NavigatorManagedData()
        self.maxTouchPoints = 0
        self.mediaCapabilities = MediaCapabilities()
        self.mediaDevices = MediaDevices()
        self.mediaSession = MediaSession()
        self.mimeTypes = MimeTypeArray
        self.onLine = True
        self.pdfViewerEnabled = True
        self.permissions = Permissions
        self.platform = 'Win32'
        self.plugins = PluginArray
        self.presentation = Presentation()
        self.product = 'Gecko'
        self.productSub = '20030107'
        self.scheduling = Scheduling()
        self.serial = Serial()
        self.serviceWorker = ServiceWorkerContainer()
        self.storage = StorageManager()
        self.storageBuckets = StorageBucketManager()
        self.usb = USB()
        self.userActivation = UserActivation()
        self.userAgent = user_agent
        self.userAgentData = NavigatorUAData(user_agent)
        self.vendor = 'Google Inc.'
        self.vendorSUb = ''
        self.virtualKeyboard = VirtualKeyboard()
        self.wakeLock = WakeLock()
        self.webdriver = False
        self.webkitPersistentStorage = DeprecatedStorageQuota()
        self.webkitTemporaryStorage = DeprecatedStorageQuota()
        self.windowControlsOverlay = WindowControlsOverlay()
        self.xr = XRSystem()
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class JSON:
    def __init__(self):
        self.parse = json.loads
        self.stringify = self._json_dumps_func
        
    def _json_dumps_func(self, data):
        return json.dumps(data, separators=(':', ','))
    
class BarProp:
    def __init__(self):
        self.visible = True
    
class Performance:
    def __init__(self, platform):
        self.platform = platform
        
        self.memory = self.pmemory()
        self.eventCounts = {
            'size': 0
        }
        self.navigation = {
            'redirectCount': 0,
            'type': 1
        }
        self.onresourcetimingbufferfull = None
        self.timeOrigin = float((int(time.time()) * 1000))
        self.timing = {}
    
    def pmemory(self):
        if self.platform == 'Android':
            js_heap_size_limit = 512 * 1024 * 1024
        else:
            js_heap_size_limit = 4 * 1024 * 1024 * 1024

        total_js_heap_size = int(js_heap_size_limit * (random.random() * 0.045 + 0.005))
        used_js_heap_size = int(total_js_heap_size * (random.random() * 0.15 + 0.8))
        
        return {
            'jsHeapSizeLimit': js_heap_size_limit,
            'totalJSHeapSize': total_js_heap_size,
            'usedJSHeapSize': used_js_heap_size
        }
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func

class Fetch:
    def __init__(self, url, headers, body):
        self.url = url
        self.headers = headers
        self.body = body
        
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
        
class Crypto:
    def digest(self, algorithm: str, data: bytes) -> bytes:
        algorithm = algorithm.lower()
        if algorithm == "sha-256":
            return hashlib.sha256(data).digest()
        elif algorithm == "sha-1":
            return hashlib.sha1(data).digest()
        elif algorithm == "sha-512":
            return hashlib.sha512(data).digest()
        else:
            raise NotImplementedError(f"Algorithm {algorithm} not implemented.")
    
    def generate_key(self, algorithm: str, length: int = 256) -> bytes:
        if algorithm.lower() == "aes-gcm":
            return os.urandom(length // 8)
        else:
            raise NotImplementedError(f"Key generation for {algorithm} not implemented.")

    def encrypt(self, key: bytes, plaintext: bytes, associated_data: bytes = b"") -> bytes:
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
        return nonce + ciphertext

    def decrypt(self, key: bytes, data: bytes, associated_data: bytes = b"") -> bytes:
        aesgcm = AESGCM(key)
        nonce = data[:12]
        ciphertext = data[12:]
        return aesgcm.decrypt(nonce, ciphertext, associated_data)
    
    def randomUUID(self):
        return str(uuid.uuid4())
    
    def getRandomValues(self, array):
        random_bytes = os.urandom(len(array) * array.itemsize)
        array.frombytes(random_bytes)
        return array
    
class CreateArrayOfBytes:
    def __init__(self, obj, array_type=numpy.uint8):
        if isinstance(obj, int):
            self.array = numpy.zeros(obj, dtype=array_type)
        elif isinstance(obj, list):
            self.array = numpy.array(obj, dtype=array_type)
            
    @property
    def byteLength(self):
        return len(self.array)
            
    def __getitem__(self, index):
        if index in dir(self):
            index_func = getattr(self, index)
            
            if not isinstance(index_func, types.FunctionType):
                return index_func
            else:
                return index_func()
        return self.array[index]
    
    def __setitem__(self, index, byte):
        if byte <= 255:
            byte = byte % 256
            
        self.array[index] = byte
        
    def __iter__(self):
        return iter(self.array)
    
    def __str__(self):
        return f'{self.array}'
    
class RegExpConstructor:
    def __init__(self, pattern, flags=''):
        flag_map = {
            'i': re.IGNORECASE,
            'm': re.MULTILINE,
            's': re.DOTALL,
            'u': 0,
        }
        re_flags = 0
        for ch in flags:
            if ch in flag_map:
                re_flags |= flag_map[ch]
        self.pattern = pattern
        self.flags = flags
        self._re = re.compile(pattern, re_flags)

        self.props = {
            'test': JSFunction(lambda this, string: self.test(string)),
            'exec': JSFunction(lambda this, string: self.exec(string)),
            'toString': JSFunction(lambda this: str(this)),
            'source': pattern,
            'flags': flags,
        }

    def test(self, string):
        return self._re.search(string) is not None

    def exec(self, string):
        match = self._re.search(string)
        if match:
            return list(match.groups()) or [match.group(0)]
        return None

    def __repr__(self):
        return f"/{self.pattern}/{self.flags}"

    def __getitem__(self, key):
        if key in self.props:
            return self.props[key]
        return getattr(self, key, None)

    def __setitem__(self, key, value):
        self.props[key] = value
        
def RegExp_constructor(this, pattern, flags='', new_target=False):
    return RegExpConstructor(pattern, flags)

RegExp = JSFunction(RegExp_constructor)
RegExp['prototype'] = {
    'toString': JSFunction(lambda this: str(this))
}
RegExp['name'] = 'RegExp'

class TextDecoder:
    def __init__(self, encoding='utf-8'):
        self.encode_type = encoding 
    
    def decode(self, encoded):
        string = ''
        if isinstance(encoded, (numpy.uint8, numpy.uint16, numpy.uint32, list)):
            for num in encoded:
                string += chr(num)
        return string.encode(self.encode_type)
    
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func

Math = {
    'trunc': math.trunc,
    'pow': math.pow,
    'floor': math.floor,
    'abs': abs,
    'ceil': math.ceil
}
    
class TextEncoder:
    def __init__(self, encoding='utf-8'):
        self.encoding_type = encoding
        
    def encode(self, string):
        string = string.encode(self.encoding_type)
        uint8_arr = numpy.zeros(len(string), dtype=numpy.uint8)
        
        for i, char in enumerate(string):
            uint8_arr[i] = ord(chr)
        return uint8_arr
    
    def __getitem__(self, key):
        if key in dir(self):
            index_func = getattr(self, key)
            return index_func
    
class JSArray(list):
    def __init__(self, *args):
        if len(args) == 1 and isinstance(args[0], int):
            super().__init__([None] * args[0])
        else:
            super().__init__(args)
            
        for name, func in Array.prototype.items():
            setattr(self, name, lambda *a, func=func: func.call(self, *a))

    def __repr__(self):
        return f'{super().__repr__()}'


class _ArrayMeta(type):
    def __getattr__(cls, name):
        if name == 'from':
            return lambda obj: JSArray(*list(obj))


class Array(metaclass=_ArrayMeta):
    prototype = {k: JSFunction(v) for k, v in ObjectPrototypeCall.array_prototype().items()}

    def __new__(cls, *args):
        return JSArray(*args)


class String:
    constructor = None
    def __call__(self, value=''):
        return str(value)
    
    def fromCharCode(self, *args):
        string = ''
        
        if len(args) == 1:
            return chr(int(args[0]))
        else:
            for arg in args:
                string += chr(arg)
        return string
    
    @property
    def prototype(self):
        return {k: JSFunction(v) for k, v in ObjectPrototypeCall.string_prototype().items()}
    
    def __getitem__(self, key):
        if key in dir(self):
            return getattr(self, key)
  
class _ObjectProto:
    def assign(target, *sources):
        if not isinstance(target, dict):
            raise TypeError('Object.assign require dict')
        
        for source in sources:
            if not isinstance(source, dict):
                continue
            
            for key, value in source.items():
                if key != '__proto__':
                    target[key] = value
        return target
    
    def get_own_property_names(obj):
        return list(obj.keys())
    
Object = {
    'prototype': {k: JSFunction(v) for k, v in ObjectPrototypeCall.object_prototype().items()},
    'assign': _ObjectProto.assign,
    'getOwnPropertyNames': _ObjectProto.get_own_property_names
}

    
class Date:
    def now():
        return int(time.time()) * 1000
    
class Blob:
    def __init__(self, parts, options=None):
        self.parts = parts
        self.type = options.get('type') if options else ''
    
    def text(self):
        return ''.join(self.parts)

    def __repr__(self):
        return f"<Blob type='{self.type}' size={len(self.text())}>"

    def toURL(self):
        return self.text()

class MessageEvent:
    def __init__(self, type_, data=None, origin='', source=None, last_event_id='', ports=None):
        self.type = type_
        self.data = data
        self.origin = origin
        self.source = source
        self.lastEventId = last_event_id
        self.ports = ports or []

    def __repr__(self):
        return f"<MessageEvent type='{self.type}' data={self.data}>"


class Worker:
    def __init__(self, blob_or_path):
        self._event_listeners = {'message': [], 'error': []}
        self._in_queue = queue.Queue()
        self._out_queue = queue.Queue()

        if isinstance(blob_or_path, Blob):
            js_code = blob_or_path.text()
        elif isinstance(blob_or_path, str):
            with open(blob_or_path, 'r') as f:
                js_code = f.read()
        else:
            raise TypeError('Expected Blob or path')

        self.ctx = quickjs.Context()
        self.ctx.add_callable("_postMessage", self._from_worker_post)

        bootstrap = """
        var postMessage = function(msg) {
            _postMessage(JSON.stringify({ data: msg }));
        };
        var onmessage = null;
        """
        self.ctx.eval(bootstrap)
        self.ctx.eval(js_code)

        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()

        threading.Thread(target=self._message_dispatcher, daemon=True).start()

    def _from_worker_post(self, raw_json):
        try:
            msg = eval(raw_json)
            evt = MessageEvent(type_='message', data=msg['data'], origin='worker')
            self._out_queue.put(evt)
        except Exception as e:
            self._emit('error', e)

    def postMessage(self, data, origin='window'):
        evt = MessageEvent(type_='message', data=data, origin=origin)
        self._in_queue.put(evt)

    def _worker_loop(self):
        while True:
            evt = self._in_queue.get()
            if evt is None:
                break
            try:
                js_event = {
                    'type': evt.type,
                    'data': evt.data,
                    'origin': evt.origin,
                    'lastEventId': evt.lastEventId,
                    'ports': evt.ports,
                    'source': evt.source
                }
                self.ctx.add_callable("__tempEvent", lambda: js_event)
                self.ctx.eval("if (typeof onmessage === 'function') onmessage(__tempEvent());")
            except Exception as e:
                self._emit('error', e)

    def addEventListener(self, event, callback):
        if event in self._event_listeners:
            self._event_listeners[event].append(callback)

    def _emit(self, event, event_obj):
        for cb in self._event_listeners.get(event, []):
            cb(event_obj)

    def _message_dispatcher(self):
        while True:
            event = self._out_queue.get()
            if event is None:
                break
            self._emit('message', event)

    def terminate(self):
        self._in_queue.put(None)
        self._out_queue.put(None)
        self.thread.join()
        
    def __getitem__(self, key):
        if key in dir(self):
            return getattr(self, key)

        
LocalStorageInit = {}
sessionStorageInit = {}
EventInit = None

class Window:
    def __init__(self, domain, user_agent, html=''):
        self.domain = domain
        self.user_Agent = user_agent
        self._html_code = html
        self.platform = 'Windows'
        self.pixels_ratio = random.uniform(0.9, 1.9)
        self.o_height, self.o_width, self.i_height, self.i_width = random.choice(list(SCREEM_RESOLUTIONS))
        
        self._event_listeners = {}
        self.on_handlers = {}
        self.activeElement = None
        self._init_env()
        
    def _init_env(self):
        self.env = {
            'chrome': CHROME_DATA,
            'clearInterval': clearInterval,
            'clearTimeout': clearTimeout,
            'closed': False,
            'clientInformation': Navigator(self.user_Agent),
            'crypto': Crypto(),
            'atob': self._atob_func,
            'btoa': self._btoa_func,
            'isSecureContext': True,
            'innerHeight': self.i_height,
            'innerWidth': self.i_width,
            'location': Location(self.domain),
            'locationbar': BarProp(),
            'length': 0,
            'name': '',
            'localStorage': LocalStorageInit,
            'sessionStorage': sessionStorageInit,
            'screen': Screen,
            'navigator': Navigator(self.user_Agent),
            'devicePixelRatio': self.pixels_ratio,
            'outerHeight': self.o_width,
            'outerWidth': self.o_height,
            'origin': 'https://' + self.domain.split('/')[2] if len(self.domain.split('/')) > 3 else self.domain,
            'pageXOffset': 0,
            'pageYOffset': 0,
            'event': EventInit,
            'performance': Performance(self.platform),
            'fetch': Fetch,
            'scrollX': 0,
            'scrollY': 0,
            'indexedDB': IDBFactory(),
            'String': String(),
            'Number': {
                'EPSILON': 2.220446049250313e-16,
                'MAX_SAFE_INTEGER': 9007199254740991,
                'MAX_VALUE': 1.7976931348623157e+308,
                'MIN_SAFE_INTEGER': -9007199254740991,
                'MIN_VALUE': 5e-324,
                'NEGATIVE_INFINITY': -math.inf,
                'NaN': math.nan,
                'POSITIVE_INFINITY': math.inf,
                'isFInite': lambda value: value > math.inf,
                'isInteger': lambda value: isinstance(value, int),
                'isNaN': lambda value: math.isnan(value),
                'isSafeInteger': lambda value: isinstance(value, int) and -(2**53 - 1) <= value <= 2**53 - 1,
                'parseFloat': self.parse_float,
                'parseInt': self.parse_int
            },
            'Object': Object,
            'decodeURI': self.decode_url_component,
            'decodeURIComponent': self.decode_url_component,
            'encodeURI': self.encode_url,
            'encodeURIComponent': self.encode_url_component,
            'statusbar': BarProp(),
            'scrollbars': BarProp(),
            'setInterval': SetInterval,
            'setTimeout': SetTimeout,
            'TextDecoder': TextDecoder,
            'TextEncoder': TextEncoder,
            'Math': Math,
            'USB': USB(),
            'console': {
                'log': print,
                'warn': print,
                'info': print,
                'dir': print,
                'error': print
            },
            'Uint8Array': lambda obj: CreateArrayOfBytes(obj, array_type=numpy.uint8),
            'Uint16Array': lambda obj: CreateArrayOfBytes(obj, array_type=numpy.uint16),
            'Uint32Array': lambda obj: CreateArrayOfBytes(obj, array_type=numpy.uint32),
            'Int8Array': lambda obj: CreateArrayOfBytes(obj, array_type=numpy.int8),
            'Int16Array': lambda obj: CreateArrayOfBytes(obj, array_type=numpy.int16),
            'Int32Array': lambda obj: CreateArrayOfBytes(obj, array_type=numpy.int32),
            'RegExp': RegExp,
            'NaN': math.nan,
            'Array': lambda obj: Array(obj),
            'Float16Array': lambda obj: CreateArrayOfBytes(obj, array_type=numpy.float16),
            'Float32Array': lambda obj: CreateArrayOfBytes(obj, array_type=numpy.float32),
            'Float64Array': lambda obj: CreateArrayOfBytes(obj, array_type=numpy.float64),
            'escape': self.escape,
            'eval': eval,
            'parseInt': self.parse_int,
            'parseFloat': self.parse_float,
            'unescape': self.unescape,
            'offscreenBuffering': True,
            'undefined': None,
            'Screen': Screen,
            'Scheduling': Scheduling,
            'Serial': Serial,
            'Window': Window,
            'PluginArray': PluginArray,
            'Bluetooth': Bluetooth,
            'requestIdleCallback': requestIdleCallback,
            'cancelIdleCallback': cancelIdleCallback,
            'addEventListener': self._addEventListener,
            'removeEventListener': self._removeEventListener,
            'dispatchEvent': self._dispatchEvent,
            'trigger_event': self.trigger_event,
            'Blob': Blob,
            'Worker': Worker,
            **WINDOW_EVENT_HANDLERS
        }
        self.env.update({
            'document': Document(self.env, self.domain, self._html_code),
        })
        self.env = {
            'window': self.env, 
            'globalThis': self.env, 
            'self': self.env,
            'parent': self.env,
            **self.env
        }
        
    def _addEventListener(self, event_type, callback):
        self._event_listeners.setdefault(event_type, []).append(callback)

    def _removeEventListener(self, event_type, callback):
        if event_type in self._event_listeners:
            self._event_listeners[event_type].remove(callback)
            
    def _dispatchEvent(self, event):
        for callback in self._event_listeners.get(event.type, []):
            callback(event)
            
        handler = self._on_handlers.get(f'on{event.type}')
        if callable(handler):
            handler(event)
            
    def trigger_event(self, event_type, event=None):
        if not event:
            event = Event(event_type)
        self._dispatchEvent(event)
        
    def _atob_func(self, b64_string):
        return b64decode(b64_string.encode()).decode()
        
    def _btoa_func(self, string):
        return b64encode(string.encode()).decode()
    
    def parse_int(self, s, radix=10):
        if not isinstance(s, str):
            s = str(s)
        s = s.lstrip()
        if radix == 0 or radix is None:
            if s.startswith(('0x', '0X')):
                radix = 16
            else:
                radix = 10
        if radix <= 10:
            pattern = fr'[0-{radix - 1}]+'
        else:
            pattern = fr'[0-9a-{chr(86 + radix)}A-{chr(54 + radix)}]+'
        match = re.match(pattern, s)
        if not match:
            return math.nan
        return int(match.group(), radix)

    
    def parse_float(self, s):
        if not isinstance(s, str):
            s = str(s)
        s = s.lstrip()

        match = re.match(r'^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?', s)
        
        if not match:
            return math.nan
        try:
            return float(match.group())
        except ValueError:
            return math.nan
    
    def unescape(self, s):
        def replace_unicode(match):
            hex_value = match.group(1)
            try:
                return chr(int(hex_value, 16))
            except:
                return match.group(0)

        s = re.sub(r'%u([0-9a-fA-F]{4})', replace_unicode, s)
        s = re.sub(r'%([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), s)
        return s
    
    def escape(self, s):
        result = ''
        
        for ch in s:
            code = ord(ch)
            if (
                0x41 <= code <= 0x5A or
                0x61 <= code <= 0x7A or
                0x30 <= code <= 0x39 or
                ch in "@*_+-./"
            ):
                result += ch
            elif code < 256:
                result += f"%{code:02X}"
            else:
                result += f"%u{code:04X}"
        return result
    
    def decode_url_component(self, encoded):
        return urllib.parse.unquote(encoded, encoding='utf-8', errors='strict')
    
    def encode_url(self, uri):
        return urllib.parse.quote(uri, safe=";/?:@&=+$,-_.!~*'()#")
    
    def encode_url_component(self, comp):
        return urllib.parse.quote(comp, safe="-_.!~*'()")
    
    def __setattr__(self, name, value):
        if name.startswith('on') and callable(value):
            self._on_handlers[name] = value
        else:
            super().__setattr__(name, value)

    def __getattr__(self, name):
        if name.startswith('on'):
            return self._on_handlers.get(name)
        raise AttributeError(f"'Window' object has no attribute '{name}'")
    
class SetInterval:
    _next_id = 0

    def __init__(self, func, delay_ms):
        self.func = func
        self.delay = delay_ms / 1000.0
        self.running = True
        self.id = SetInterval._next_id
        SetInterval._next_id += 1
        _active_intervals[self.id] = self
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while self.running:
            time.sleep(self.delay)
            if self.running:
                self.func()

    def stop(self):
        self.running = False
        _active_intervals.pop(self.id, None)
            
class SetTimeout:
    _next_id = 0

    def __init__(self, func, delay_ms):
        self.func = func
        self.delay = delay_ms / 1000.0
        self.cancelled = False
        self.id = SetTimeout._next_id
        SetTimeout._next_id += 1
        _active_timeouts[self.id] = self
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        time.sleep(self.delay)
        if not self.cancelled:
            self.func()
        _active_timeouts.pop(self.id, None)

    def cancel(self):
        self.cancelled = True
        _active_timeouts.pop(self.id, None)
        
def clearInterval(interval_id):
    interval = _active_intervals[interval_id]
    if interval:
        interval.stop()
        
def clearTimeout(timeout_id):
    timeout = _active_timeouts[timeout_id]
    if timeout:
        timeout.cancel()
        
def requestIdleCallback(callback, timeout=None):
    def wrapper():
        start = time.time()
        
        deadline = {
            'didTimeout': False,
            'timeRemaining': lambda: max(0, 50 - (time.time() - start) * 1000)
        }
        callback(deadline)
    delay = 0.001
    timer = threading.Timer(delay, wrapper)
    timer.start()
    return time

def cancelIdleCallback(timer):
    timer.cancel()
    
if __name__ == '__main__':
    data = {'test_1': 10, 'test_2': 20}
    print(Object['prototype']['hasOwnProperty'].call(data, 'test_143'))
    sys.exit()
    url = 'https://nopecha.com/demo/cloudflare'
    window = Window(
        domain=url,
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
    )