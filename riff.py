import struct
# https://vstcpp.wpblog.jp/?p=2090

# Riff
# + List(INFO)
# |L Elements
# + List(sdta)
# |L Elements
# L List(pdta)
#  + PhdrRoot(phdr)
#  |+ Phdr
#  |L EOP(presetBagInde=バッグ総数)
#  + PbagRoot(pbag)
#  |+ Pbag
#  |L EOB(pmod, pgenの総数)
#  + PmodRoot(pmod)
#  |+ Pmod
#  |L EOM (0fill)
#  + PgenRoot(pgen)
#  |+ Pgen
#  |L EOG (0fill)
#  + Elements


def get(l, n):
    if isinstance(l, List):
        l = l.data
    for i in l:
        if isinstance(n, str):
            if i.name == n:
                return i
        else:
            if isinstance(i, n):
                return i
    return None


class RiffParent:
    def __init__(self, tag, name, data, _str_header):
        self.tag = tag
        self.name = name
        self.data = data
        self._str_header = _str_header

    def __str__(self):
        for i in self.data:
            s += str(i) + ", "
        s = s.rstrip(", ")
        return f"{self._str_header}:[{s}]"

    def size(self):
        s = 4
        for i in self.data:
            s += i.size() + 8
        return s

    def write(self, istream, ostream):
        ostream.write(struct.pack("<4sl4s", self.tag.encode(),
                                  self.size(), self.name.encode()))
        for i in self.data:
            i.write(istream, ostream)


class Riff(RiffParent):
    def __init__(self, tag, form, data, fname):
        super().__init__(tag, form, data, f"{fname} RIFF")
        self.form = form
        self.fname = fname
        pdta = get(data, "pdta")
        self.phdr = get(pdta, PhdrRoot)
        pbag = get(pdta, PbagRoot)
        pmod = get(pdta, PmodRoot)
        pgen = get(pdta, PgenRoot)
        self.phdr.init(pbag, pmod, pgen)

    def write(self, fname):
        with open(fname, 'wb') as fo:
            with open(self.fname, 'rb') as fi:
                super().write(fi, fo)


class List(RiffParent):
    def __init__(self, tag, name, data):
        super().__init__(tag, name, data, f"{tag}:{name}")


class Element:
    def __init__(self, tag, size, fofset):
        self.tag = tag
        self._size = size
        self.fofset = fofset

    def __str__(self):
        return f"{self.tag}({self._size})"

    def size(self):
        return self._size

    def write(self, istream, ostream):
        ostream.write(struct.pack("<4sl", self.tag.encode(), self._size))
        istream.seek(self.fofset)
        ostream.write(istream.read(self._size))


class PElementRoot:
    def __init__(self, tag, data, last):
        self.tag = tag
        self.data = data
        self.last = last

    def __str__(self):
        s = f"{self.tag}({self.size()}):["
        for i in self.data:
            s += str(i) + ", "
        s = s.rstrip(", ") + "]"
        return s

    def data_with_end(self):
        return self.data + [self.last]

    def size(self):
        s = self.last.size()
        for i in self.data:
            s += i.size()
        return s

    def write(self, istream, ostream):
        ostream.write(struct.pack("<4sl", self.tag.encode(), self.size()))
        for p in self.data:
            p.write(istream, ostream)
        self.last.write(istream, ostream)


class PhdrRoot(PElementRoot):
    def __init__(self, tag, data):
        tmp = []
        for d in data:
            if d.name == "EOP":
                self.eop = d
            else:
                tmp.append(d)
        super().__init__(tag, tmp, self.eop)

    def sort(self):
        self.data = sorted(self.data, key=lambda t: t.name)

    def init(self, pbag, pmod, pgen):
        self.pbag = pbag
        self.pmod = pmod
        self.pgen = pgen
        pbag = pbag.data_with_end()
        pmod = pmod.data_with_end()
        pgen = pgen.data_with_end()
        data = self.data_with_end()
        for i, n in zip(data[:-1], data[1:]):
            b = pbag[i.bagIndex:n.bagIndex+1]
            for j, nj in zip(b[:-1], b[1:]):
                j.gen = pgen[j.genIndex:nj.genIndex]
                j.mod = pmod[j.modIndex:nj.modIndex]
            i.bag = b[:-1]

    def update(self):
        self.pbag.data.clear()
        self.pmod.data.clear()
        self.pgen.data.clear()
        bidx = 0
        midx = 0
        gidx = 0
        for i in self.data:
            i.bagIndex = bidx
            for b in i.bag:
                b.genIndex = gidx
                for g in b.gen:
                    self.pgen.data.append(g)
                    gidx += 1
                for m in b.mod:
                    self.pmod.data.append(m)
                    midx += 1
                self.pbag.data.append(b)
                bidx += 1
        self.eop.bagIndex = bidx
        self.pbag.eob.genIndex = gidx
        self.pbag.eob.modIndex = midx

    def write(self, istream, ostream):
        self.update()
        super().write(istream, ostream)


class Phdr:
    def __init__(self, name, presentno, bank, bagIndex, r0, r1, r2):
        self.name = name
        self.presentno = presentno
        self.bank = bank
        self.bagIndex = bagIndex  # プリセット順に必ず増える必要がある
        self.r0 = r0
        self.r1 = r1
        self.r2 = r2
        self.bag = []

    def __str__(self):
        s = ""
        for i in self.bag:
            s += str(i) + ", "
        s = s.rstrip(", ")
        return f"{self.name}-{self.bank}/{self.presentno}({self.bagIndex}[{s}])"

    def key(self):
        return f"{self.bank}/{self.presentno}"

    def size(self):
        return 38

    def write(self, istream, ostream):
        ostream.write(struct.pack("<20shhhlll", self.name.encode(
        ), self.presentno, self.bank, self.bagIndex, self.r0, self.r1, self.r2))


class PbagRoot(PElementRoot):
    def __init__(self, tag, data):
        self.eob = data[-1]
        super().__init__(tag, data[:-1], self.eob)


class Pbag:
    def __init__(self, genIndex, modIndex):
        self.genIndex = genIndex  # unsigned short
        self.modIndex = modIndex  # unsigned short
        self.gen = []
        self.mod = []

    def __str__(self):
        gs = ""
        for i in self.gen:
            gs += str(i) + ", "
        gs = gs.rstrip(", ")
        ms = ""
        for i in self.mod:
            ms += str(i) + ", "
        ms = ms.rstrip(", ")
        return f"<{self.genIndex}:[{gs}], {self.modIndex}:[{ms}]>"

    def size(self):
        return 4

    def write(self, istream, ostream):
        ostream.write(struct.pack("<HH", self.genIndex, self.modIndex))


class PmodRoot(PElementRoot):
    def __init__(self, tag, data):
        self.eom = data[-1]
        super().__init__(tag, data[:-1], self.eom)


class Pmod:
    def __init__(self, srcOper, dstOper, modAmount, amtSrcOper, modTransOper):
        self.srcOper = srcOper              # unsigned short
        self.dstOper = dstOper              # unsigned short
        self.modAmount = modAmount          # short
        self.amtSrcOper = amtSrcOper        # unsigned short
        self.modTransOper = modTransOper    # unsigned short

    def __str__(self):
        return f"{self.srcOper}-{self.dstOper}"

    def size(self):
        return 10

    def write(self, istream, ostream):
        ostream.write(struct.pack("<HHhHH", self.srcOper, self.dstOper,
                                  self.modAmount, self.amtSrcOper, self.modTransOper))


class PgenRoot(PElementRoot):
    def __init__(self, tag, data):
        self.eog = data[-1]
        super().__init__(tag, data[:-1], self.eog)


class Pgen:
    def __init__(self, genOper, genAmount):
        self.genOper = genOper      # unsigned short
        self.genAmount = genAmount  # short

    def __str__(self):
        return f"{self.genOper}:{self.genAmount}"

    def size(self):
        return 4

    def write(self, istream, ostream):
        ostream.write(struct.pack("<Hh", self.genOper, self.genAmount))


def __parse(f):
    tag = f.read(4).decode("ascii")
    size = struct.unpack_from("<l", f.read(4))[0]
    start = f.tell()
    if tag == "RIFF":
        tmp = []
        form = f.read(4).decode("ascii")
        while f.tell() - start < size:
            tmp.append(__parse(f))
        return Riff(tag, form, tmp, f.name)
    if tag == "LIST":
        name = f.read(4).decode("ascii")
        ret = List(tag, name, [])
        while f.tell() - start < size:
            ret.data.append(__parse(f))
        return ret
    if tag == "phdr":
        phdrs = []
        while f.tell() - start < size:
            name = f.read(20)
            name = name[0:name.find(0)].decode('ascii')
            d = struct.unpack_from("<hhhlll", f.read(18))
            e = Phdr(name, *d)
            phdrs.append(e)
        return PhdrRoot(tag, phdrs)
    if tag == "pbag":
        pbags = []
        while f.tell() - start < size:
            d = struct.unpack_from("<HH", f.read(4))
            pbags.append(Pbag(*d))
        return PbagRoot(tag, pbags)
    if tag == "pmod":
        pmods = []
        while f.tell() - start < size:
            d = struct.unpack_from("<HHhHH", f.read(10))
            pmods.append(Pmod(*d))
        return PmodRoot(tag, pmods)
    if tag == "pgen":
        pgens = []
        while f.tell() - start < size:
            d = struct.unpack_from("<Hh", f.read(4))
            pgens.append(Pgen(*d))
        return PgenRoot(tag, pgens)
    f.seek(start + size)
    return Element(tag, size, start)


def read(fname):
    with open(fname, 'rb') as f:
        r = __parse(f)
        return r
