import struct

from collections import namedtuple
Riff = namedtuple('RIFF', ('tag', 'size', 'form', 'data'))
List = namedtuple('LIST', ('tag', 'size', 'name', 'fofset', 'data'))
Element = namedtuple('ELEM', ('tag', 'size', 'fofset'))
PhdrRoot = namedtuple('PHRT', ('tag', 'size', 'fofset', 'data'))
Phdr = namedtuple('PHDR', ('name', 'presentno', 'bank', 'bagIndex', 'r0', 'r1', 'r2'))
def parse(f):
    tag = f.read(4).decode("ascii")
    size = struct.unpack_from("<l", f.read(4))[0]
    start = f.tell()
    if tag == "RIFF":
        ret =  Riff(tag, size, f.read(4).decode("ascii"), [])
        while f.tell() - start < size:
            ret.data.append(parse(f))
        return ret
    if tag == "LIST":
        name = f.read(4).decode("ascii")
        ret =  List(tag, size, name, start, [])
        while f.tell() - start < size:
            ret.data.append(parse(f))
        return ret
    if tag == "phdr":
        ret = PhdrRoot(tag, size, start, [])
        while f.tell() - start < size:
            name = f.read(20)
            name = name[0:name.find(0)].decode('ascii')
            d = struct.unpack_from("<hhhlll", f.read(18))
            e = Phdr(name, *d)
            ret.data.append(e)
        return ret
    
    f.seek(start + size)
    return Element(tag, size, start)
def test():
    with open('test.sf2', 'rb') as f:
        print(parse(f))
test()

