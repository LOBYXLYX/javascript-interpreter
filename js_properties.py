import re
import sys
import types

class ObjectInterpreter:
    def __init__(self, obj):
        self.obj = obj
        
    def __getitem__(self, key):
        #print('GET ITEM', key, self.obj)
        if isinstance(key, types.FunctionType):
            return key
        
    def __call__(self, *args):
        print('CALL FUNCTION', args)

    def __setitem__(self, key, value):
        print('SET ITEM', key, value)
        
class JSFunction:
    def __init__(self, func):
        self.func = func
        self.bound_this = None
        self.bound_args = ()
        
    def __call__(self, *args, **kwds):
        self.func(*args, **kwds)

    def call(self, this, *args, **kwargs):
        return self.func(this, *args, **kwargs)
    
    def bind(self, *bound_args):
        bound_func = JSFunction(self.func)
        bound_func.bound_args = bound_args
        return bound_func
    
    def __getitem__(self, key):
        if key in dir(self):
            return getattr(self, key)
        
class Number:
    def __init__(self, value):
        self.value = value
        self.props = {}

    def __getitem__(self, key):
        return self.props.get(key)

    def __setitem__(self, key, value):
        self.props[key] = value

    def __repr__(self):
        return str(self.value)

    def valueOf(self):
        return self.value
    
class Object:
    def __init__(self, proto=None):
        self.props = {}
        self.__proto__ = proto

    def __getitem__(self, key):
        if key in self.props:
            return self.props[key]
        if self.__proto__ and isinstance(self.__proto__, Object):
            return self.__proto__[key]

    def __setitem__(self, key, value):
        self.props[key] = value

    def hasOwnProperty(self, key):
        return key in self.props

    def get_own_property_keys(self):
        return list(self.props.keys())

    def __repr__(self):
        return f"Object({self.props}, proto={self.__proto__})"
    
class ObjectProto:
    def __init__(self, func):
        self.func = func
        
    def __call__(self, *args, **kwds):
        self.func(*args, **kwds)
        
    def create(self, proto, properties=None):
        obj = Object(proto)

        if properties:
            for key, descriptor in properties.items():
                if isinstance(descriptor, dict) and 'value' in descriptor:
                    obj[key] = descriptor['value']
                else:
                    obj[key] = descriptor
        return obj

        
    def __getitem__(self, key):
        if key in dir(self):
            return getattr(self, key)
            
class Prototype:
    def object_properties(obj, prop):
        inter_obj = ObjectInterpreter(obj)
        
        if isinstance(prop, list):
            prop = ''
            
        if prop in obj and isinstance(obj, dict):
            return obj, prop
        
        if isinstance(obj, list):
            array_proto = Prototype.array_prototype(obj)
            return array_proto, prop
        
        elif isinstance(obj, str):
            string_proto = Prototype.string_prototype(obj)
            return string_proto, prop
        
        elif isinstance(obj, dict):
            object_proto = Prototype.object_prototype(obj)
            return object_proto, prop
        
        if isinstance(obj, int):
            print(obj)
            
    def object_properties2(obj):
        if isinstance(obj, int):
            return Number(obj)
        return obj
        
    def _to_string36(n):
        chars = '0123456789abcdefghijklmnopqrstuvwxyz'
        result = ''
        while n:
            n, r = divmod(n, 36)
            result = chars[r] + result
        return result or '0'
    
    def number_prototype(number):
        return {
            'toString': lambda this=None: str(number)
        }
        
    def array_prototype(array, return_protos=False):
        def _prototypes(array):
            array_obj = {
                'length': len(array),
                '__proto__': {}
            }

            def update_length():
                array_obj['length'] = len(array)

            array_obj['push'] = lambda *args, this=None: (
                array.extend(args),
                update_length(),
                len(array)
            )[-1]

            array_obj['pop'] = lambda this=None: (
                array.pop(),
                update_length()
            )[0]

            array_obj['shift'] = lambda this=None: (
                array.pop(0),
                update_length()
            )[0]

            array_obj['unshift'] = lambda *args, this=None: (
                [array.insert(i, arg) for i, arg in enumerate(reversed(args))],
                update_length(),
                len(array)
            )[-1]

            array_obj['slice'] = lambda start=0, end=None, this=None: array[start:end]
            array_obj['splice'] = lambda start, delete_count=None, *items, this=None: (
                lambda deleted: (
                    array.__setitem__(slice(start, start + delete_count), items),
                    update_length(),
                    deleted
                )[-1]
            )([array[i] for i in range(start, start + (delete_count or len(array))) if i < len(array)])

            array_obj['indexOf'] = lambda val, this=None: array.index(val) if val in array else -1
            array_obj['includes'] = lambda val, this=None: val in array
            array_obj['join'] = lambda sep=',', this=None: sep.join(str(x) for x in array)
            array_obj['reverse'] = lambda this=None: (array.reverse(), array_obj)[1]
            array_obj['map'] = lambda fn, this=None: [fn(x) for x in array]
            array_obj['forEach'] = lambda fn, this=None: [fn(x) for x in array]
            array_obj['filter'] = lambda fn, this=None: [x for x in array if fn(x)]
            array_obj['some'] = lambda fn, this=None: any(fn(x) for x in array)
            array_obj['every'] = lambda fn, this=None: all(fn(x) for x in array)
            array_obj['find'] = lambda fn, this=None: next((x for x in array if fn(x)), None)
            array_obj['findIndex'] = lambda fn, this=None: next((i for i, x in enumerate(array) if fn(x)), -1)
            array_obj['reduce'] = lambda fn, initial=None, this=None: (
                lambda acc, items: (
                    lambda result: result
                )(acc if not items else __import__('functools').reduce(fn, items, acc))
            )(initial, array if initial is not None else array[1:])

            array_obj['fill'] = lambda value, start=0, end=None, this=None: (
                [array.__setitem__(i, value) for i in range(start, end or len(array))],
                array
            )[-1]

            array_obj['concat'] = lambda *args, this=None: Prototype.array_prototype([
                *array, *(item if isinstance(item, list) else [item] for arg in args for item in (arg if isinstance(arg, list) else [arg]))
            ])

            array_obj['toString'] = lambda this=None: ','.join(str(x) for x in array)

            for idx, val in enumerate(array):
                array_obj[idx] = val

            array_obj['__proto__'] = {'constructor': 'Array'}
            
            for name, func in array_obj.items():
                if callable(func):
                    array_obj[name] = JSFunction(func)
                else:
                    array_obj[name] = func
            return array_obj

        if return_protos:
            return _prototypes
        return _prototypes(array)
    
    def object_prototype(obj):
        objects = {
            'constructor': lambda this=None: dict,
            'hasOwnProperty': lambda key, this=None: key in obj if isinstance(obj, dict) else hasattr(obj, key),
            'toString': lambda this=None: f'[object {type(obj).__name__}]',
            'valueOf': lambda this=None: obj,
            'keys': lambda this=None: list(obj.keys()) if isinstance(obj, dict) else [],
            'values': lambda this=None: list(obj.values()) if isinstance(obj, dict) else [],
            'entries': lambda this=None: list(obj.items()) if isinstance(obj, dict) else [],
            '__proto__': {
                'constructor': 'Object'
            },
        }
        
        objects = {k: ObjectProto(v) for k, v in objects.items()}
        objects['trustedTypes'] = None
        return objects
    
    def string_prototype(string, return_protos=False):
        def to_py_str(val):
            return str(val) if val is not None else ""

        def _prototypes(string):
            return {
                'length': len(string),
                'charAt': lambda index: string[index] if 0 <= index < len(string) else '',
                'charCodeAt': lambda index: ord(string[index]) if 0 <= index < len(string) else None,
                'codePointAt': lambda index: ord(string[index]) if 0 <= index < len(string) else None,
                'includes': lambda substr, start=0: substr in string[start:],
                'indexOf': lambda substr, start=0: string.find(substr, start),
                'lastIndexOf': lambda substr: string.rfind(substr),
                'startsWith': lambda substr, start=0: string.startswith(substr, start),
                'endsWith': lambda substr, length=None: string[:length].endswith(substr) if length else string.endswith(substr),
                'slice': lambda start, end=None: string[start:end],
                'substring': lambda start, end=None: string[min(start, end or len(string)):max(start, end or len(string))],
                'substr': lambda start, length=None: string[start:start + length] if length is not None else string[start:],
                'toLowerCase': lambda: string.lower(),
                'toUpperCase': lambda: string.upper(),
                'toLocaleLowerCase': lambda: string.lower(),
                'toLocaleUpperCase': lambda: string.upper(),
                'trim': lambda: string.strip(),
                'trimStart': lambda: string.lstrip(),
                'trimEnd': lambda: string.rstrip(),
                'trimLeft': lambda: string.lstrip(),
                'trimRight': lambda: string.rstrip(),
                'repeat': lambda count: string * count,
                'padStart': lambda targetLength, padString=' ': string.rjust(targetLength, padString),
                'padEnd': lambda targetLength, padString=' ': string.ljust(targetLength, padString),
                'split': lambda sep=None, limit=None: (string.split(sep) if sep is not None else list(string))[:limit] if limit else (string.split(sep) if sep is not None else list(string)),
                'replace': lambda pattern, replacement: re.sub(pattern, replacement, string, count=1),
                'replaceAll': lambda pattern, replacement: re.sub(pattern, replacement, string),
                'match': lambda pattern: re.findall(pattern, string),
                'matchAll': lambda pattern: list(re.finditer(pattern, string)),
                'search': lambda pattern: (m := re.search(pattern, string)).start() if m else -1,
                'concat': lambda *args: string + ''.join(map(to_py_str, args)),
                'toString': lambda: string,
                'valueOf': lambda: string,
                'join': lambda sep: string.join(sep)
            }
            
        if return_protos:
            return _prototypes
        return _prototypes(string)