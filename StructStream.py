#!/usr/bin/env python3
import struct

class Types:
    def __init__(self):
        self.structTypes = {
            "Int8": "b",
            "UInt8": "B",
            "Int16": "h",
            "UInt16": "H",
            "Int32": "i",
            "UInt32": "I",
            "Int64": "q",
            "UInt64": "Q",
            "Int8": "b",
            "Half": "e",
            "Float": "f",
            "Double": "d",
            "Char": "s"
        }
        for name in self.structTypes:
            setattr(self, name, self.structTypes[name])

    def __iter__(self):
        return iter(self.structTypes)

    def __getitem__(self, a):
        return self.structTypes[a]

Types = Types()

def SingleFromStruct(read, st, data = None):
    cls = struct.Struct(st)
    def func():
        if data:
            return handle.write(cls.pack(data))
        else:
            return cls.unpack(handle.read(cls.size))[0]
    return func

def compileStruct(strt, endianness = "<"):
    i = 0
    l = len(strt)
    elements = 0
    format = endianness
    groups = []
    while i < l:
        t = strt[i]
        n = strt[i+1]
        if type(t) != str or type(n) != str:
            raise ValueError("Malformed struct!")
        i += 2
        length = 1
        if i < l and type(strt[i]) == int:
            length = strt[i]
            i += 1
        format += "{}{}".format(length, t)
        if t == "s" or t == "p":
            length = 1
        elements += length
        groups.append((n, length, t))
    strct = struct.Struct(format)

    def func(handle, data = None):
        if data: #Write
            result = [None] * elements
            i = 0
            #Dictionary representation
            if isinstance(data, dict):
                for group in groups:
                    if group[1] == 1:
                        result[i] = data[group[0]]
                        i += 1
                    else:
                        for x in range(len(data[group[0]])):
                            result[i] = data[group[0]][x]
                            i += 1
            
            #List representation
            elif isinstance(data, (tuple, list)):
                ii = 0
                for group in groups:
                    if group[1] == 1:
                        result[i] = data[ii]
                        i += 1
                        ii += 1
                    else:
                        for x in range(len(data[ii])):
                            result[i] = data[ii][x]
                            i += 1
                        ii += 1
            
            return handle.write(strct.pack(*result))
        
        else: #Read
            data = handle.read(strct.size)
            if len(data) != strct.size:
                return None
            data = strct.unpack(data)
            result = {}
            i = 0
            for group in groups:
                if group[1] == 1:
                    result[group[0]] = data[i]
                    i += 1
                else:
                    result[group[0]] = []
                    for ii in range(group[1]):
                        result[group[0]].append(data[i])
                        i += 1
                    result[group[0]] = tuple(result[group[0]])
            return result
    return func

class WithPop(object):
    def __init__(self, position, direction, handle):
        self.position = position
        self.direction = direction
        self.handle = handle
      
    def __enter__(self):
        self.handle.push(self.position, self.direction)
  
    def __exit__(self, *args):
        self.handle.pop()

class StructStream:
    def __init__(self, handle, endianness = "<"):
        self.structCache = {}
        self.stack = []
        self.handle = handle
        #Install struct types
        for name in Types:
            if hasattr(self, name):
                continue
            setattr(self, name, SingleFromStruct(handle.read, endianness+Types[name]))

    def Char(self, l = None, data = None):
        if data:
            l = l or len(data)
            return self.handle.write(data[:l].ljust(l, b'\0'))
        else:
            return self.handle.read(l or 1)
    
    def readStruct(self, struc):
        if hash(struc) not in self.structCache:
            self.structCache[hash(struc)] = compileStruct(struc)
        return self.structCache[hash(struc)](self.handle)
    
    def writeStruct(self, struc, data):
        if hash(struc) not in self.structCache:
            self.structCache[hash(struc)] = compileStruct(struc)
        return self.structCache[hash(struc)](self.handle, data)
    
    def seek(self, position, direction = 0):
        return self.handle.seek(position, direction)
    
    def tell(self):
        return self.handle.tell()
    
    def read(self, *args):
        return self.handle.read(*args)
    
    def push(self, position = None, direction = 0):
        if position == None:
            position = self.tell()
        self.stack.append(self.tell())
        self.seek(position, direction)
    
    def pushing(self, position = None, direction = 0):
        if position == None:
            position = self.tell()
        return WithPop(position, direction, self)
    
    def pop(self):
        self.handle.seek(self.stack.pop())

if __name__ == "__main__":
    import io
    T = Types
    TestHeader = (
        T.Char,   "magic", 4,
        T.UInt8,  "version",
        T.UInt32, "crc",
        T.UInt32, "flags",
    )
    
    data = io.BytesIO()
    handle = StructStream(data)
    with handle.pushing():
        handle.writeStruct(TestHeader, {
            "magic": b"asdf",
            "version": 1,
            "crc": 0xAABBCCDD,
            "flags": 12345678
        })
    
    print(handle.readStruct(TestHeader))
    
    with handle.pushing():
        handle.writeStruct(TestHeader, (
            b"asdf",
            1,
            0xAABBCCDD,
            12345678
        ))
    
    print(handle.readStruct(TestHeader))