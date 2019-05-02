import struct
class Riff:
    def __init__(self, tag, size, form, data, fname):
        self.tag = tag
        self.size = size
        self.form = form
        self.data = data
        self.fname = fname
    def __str__(self):
        s = f"{self.fname} RIFF:["
        for i in self.data:
            s += str(i) + ", "
        s = s.rstrip(", ") + "]"
        return s
    def phdr(self):
        def f(r):
            if isinstance(r, PhdrRoot):
                return r.data
            if isinstance(r, Element):
                return None
            for i in r.data:
                j = f(i)
                if j is not None:
                    return j
        return f(self)
        
class List:
    def __init__(self, tag, size, name, fofset, data):
        self.tag = tag
        self.size = size
        self.name = name
        self.fofset = fofset
        self.data = data
    def __str__(self):
        s =  f"{self.tag}:{self.name}["
        for i in self.data:
            s += str(i) + ", "
        s = s.rstrip(", ") + "]"
        return s
        
class Element:
    def __init__(self, tag, size, fofset):
        self.tag = tag
        self.size = size
        self.fofset = fofset
    def __str__(self):
        return f"{self.tag}({self.size})"
        
class PhdrRoot:
    def __init__(self, tag, size, fofset, data):
        self.tag = tag
        self.size = size
        self.fofset = fofset
        self.data = data
    def __str__(self):
        s = f"{self.tag}({self.size}):["
        for i in self.data:
            s += str(i) + ", "
        s = s.rstrip(", ") + "]"
        return s
class Phdr:
    def __init__(self, name, presentno, bank, bagIndex, r0, r1, r2):
        self.name = name
        self.presentno = presentno
        self.bank = bank
        self.bagIndex = bagIndex
        self.r0 = r0
        self.r1 = r1
        self.r2 = r2
    def __str__(self):
        return f"{self.name}-{self.bank}/{self.presentno}"

def __parse(f):
    tag = f.read(4).decode("ascii")
    size = struct.unpack_from("<l", f.read(4))[0]
    start = f.tell()
    if tag == "RIFF":
        ret =  Riff(tag, size, f.read(4).decode("ascii"), [], f.name)
        while f.tell() - start < size:
            ret.data.append(__parse(f))
        return ret
    if tag == "LIST":
        name = f.read(4).decode("ascii")
        ret =  List(tag, size, name, start, [])
        while f.tell() - start < size:
            ret.data.append(__parse(f))
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

def read(fname):
    with open(fname, 'rb') as f:
        return __parse(f)
        
def __write(fo, fi, e):
    if e.tag == "RIFF":
        fo.write(struct.pack("<4sl4s", e.tag.encode(), e.size, e.form.encode()))
        for i in e.data:
            __write(fo, fi, i)
    elif e.tag == "LIST":
        fo.write(struct.pack("<4sl4s", e.tag.encode(), e.size, e.name.encode()))
        for i in e.data:
            __write(fo, fi, i)
    elif e.tag == "phdr":
        e.size = 38 * len(e.data)
        fo.write(struct.pack("<4sl", e.tag.encode(), e.size))
        for i in e.data:
            fo.write(struct.pack("<20shhhlll", i.name.encode(), i.presentno, i.bank, i.bagIndex, i.r0, i.r1, i.r2))
    else:
        fo.write(struct.pack("<4sl", e.tag.encode(), e.size))
        fi.seek(e.fofset)
        fo.write(fi.read(e.size))
        
def write(fname, riff):
    with open(fname, 'wb') as fo:
        with open(riff.fname, 'rb') as fi:
            __write(fo, fi, riff)
