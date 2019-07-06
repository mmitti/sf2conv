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

class Riff:
    def __init__(self, tag, size, form, data, fname):
        self.tag = tag
        self.size = size
        self.form = form
        self.fname = fname
        self.data = data
        pdta = get(data, "pdta")
        
        self.phdr = get(pdta, PhdrRoot)
        pbag = get(pdta, PbagRoot)
        pmod = get(pdta, PmodRoot)
        pgen = get(pdta, PgenRoot)
        self.phdr.init(pbag, pmod, pgen)

    def __str__(self):
        s = f"{self.fname} RIFF:["
        for i in self.data:
            s += str(i) + ", "
        s = s.rstrip(", ") + "]"
        return s
        
    def _size(self):
        self.size = 4
        for i in self.data:
            self.size += i._size() + 8
        return self.size

    def _write(self, istream, ostream):
        ostream.write(struct.pack("<4sl4s", self.tag.encode(), self._size(), self.form.encode()))
        for i in self.data:
            i._write(istream, ostream)

class List:
    def __init__(self, tag, size, name, fofset, data):
        self.tag = tag
        self.size = size
        self.name = name
        self.fofset = fofset
        self.data = data

    def __str__(self):
        s = f"{self.tag}:{self.name}["
        for i in self.data:
            s += str(i) + ", "
        s = s.rstrip(", ") + "]"
        return s
        
    def _size(self):
        self.size = 4
        for i in self.data:
            self.size += i._size() + 8
        return self.size

    def _write(self, istream, ostream):
        ostream.write(struct.pack("<4sl4s", self.tag.encode(), self._size(), self.name.encode()))
        for i in self.data:
            i._write(istream, ostream)


class Element:
    def __init__(self, tag, size, fofset):
        self.tag = tag
        self.size = size
        self.fofset = fofset
    def __str__(self):
        return f"{self.tag}({self.size})"
    def _size(self):
        return self.size
    def _write(self, istream, ostream):
        ostream.write(struct.pack("<4sl", self.tag.encode(), self.size))
        istream.seek(self.fofset)
        ostream.write(istream.read(self.size))

class PElementRoot(Element):
    def __init__(self, tag, size, fofset, data):
        super().__init__(tag, size, fofset)
        self.data = data
        
    def __str__(self):
        s = f"{self.tag}({self.size}):["
        for i in self.data:
            s += str(i) + ", "
        s = s.rstrip(", ") + "]"
        return s

class PhdrRoot(PElementRoot) :
    def __init__(self, tag, size, fofset, data):
        tmp = []
        for d in data:
            if d.name == "EOP":
                self.eop = d
            else:
                tmp.append(d)
        super().__init__(tag, size, fofset, tmp)
    def sort(self):
        self.data = sorted(self.data, key=lambda t: t.name)
    
    def init(self, pbag, pmod, pgen):
        self.pbag = pbag
        self.pmod = pmod
        self.pgen = pgen
        pbag = pbag.data + [pbag.eob]
        pmod = pmod.data + [pmod.eom]
        pgen = pgen.data + [pgen.eog]
        data = self.data + [self.eop]
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
                    gidx+=1
                for m in b.mod:
                    self.pmod.data.append(m)
                    midx+=1
                self.pbag.data.append(b)
                bidx+=1
        self.eop.bagIndex = bidx
        self.pbag.eob.genIndex = gidx
        self.pbag.eob.modIndex = midx
    
    def _size(self):
        self.size = (len(self.data) + 1) * 38
        return self.size

    def _write(self, istream, ostream):
        self.update()
        ostream.write(struct.pack("<4sl", self.tag.encode(), self._size()))
        for p in self.data + [self.eop]:
            ostream.write(struct.pack("<20shhhlll", p.name.encode(), p.presentno, p.bank, p.bagIndex, p.r0, p.r1, p.r2))

class Phdr:
    def __init__(self, name, presentno, bank, bagIndex, r0, r1, r2):
        self.name = name
        self.presentno = presentno
        self.bank = bank
        self.bagIndex = bagIndex # プリセット順に必ず増える必要がある
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

class PbagRoot(PElementRoot):
    def __init__(self, tag, size, fofset, data):
        super().__init__(tag, size, fofset, data[:-1])
        self.eob = data[-1]
    def _size(self):
        self.size = (len(self.data) + 1) * 4
        return self.size
    def _write(self, istream, ostream):
        ostream.write(struct.pack("<4sl", self.tag.encode(), self._size()))
        for b in self.data + [self.eob]:
            ostream.write(struct.pack("<HH", b.genIndex, b.modIndex))
class Pbag:
    def __init__(self, genIndex, modIndex):
        self.genIndex = genIndex # unsigned short
        self.modIndex = modIndex # unsigned short
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
        
class PmodRoot(PElementRoot):
    def __init__(self, tag, size, fofset, data):
        super().__init__(tag, size, fofset, data[:-1])
        self.eom = data[-1]
    def _size(self):
        self.size = (len(self.data) + 1) * 10
        return self.size
    def _write(self, istream, ostream):
        ostream.write(struct.pack("<4sl", self.tag.encode(), self._size()))
        for m in self.data + [self.eom]:
            ostream.write(struct.pack("<HHhHH", m.srcOper, m.dstOper, m.modAmount, m.amtSrcOper, m.modTransOper))
class Pmod:
    def __init__(self, srcOper, dstOper, modAmount, amtSrcOper, modTransOper):
        self.srcOper = srcOper              # unsigned short
        self.dstOper = dstOper              # unsigned short
        self.modAmount = modAmount          # short
        self.amtSrcOper = amtSrcOper        # unsigned short
        self.modTransOper = modTransOper    # unsigned short
    def __str__(self):
        return f"{self.srcOper}-{self.dstOper}"

class PgenRoot(PElementRoot):
    def __init__(self, tag, size, fofset, data):
        super().__init__(tag, size, fofset, data[:-1])
        self.eog = data[-1]
    def _size(self):
        self.size = (len(self.data) + 1) * 4
        return self.size
    def _write(self, istream, ostream):
        ostream.write(struct.pack("<4sl", self.tag.encode(), self._size()))
        for g in self.data + [self.eog]:
            ostream.write(struct.pack("<Hh", g.genOper, g.genAmount))
class Pgen:
    def __init__(self, genOper, genAmount):
        self.genOper = genOper      # unsigned short
        self.genAmount = genAmount  # short
        
    def __str__(self):
        return f"{self.genOper}:{self.genAmount}"


# struct SFBag // pbag,ibagチャンク用の構造体 4byte
# {
# 	unsigned short genIndex;
# 	unsigned short modIndex;
# };
# struct SFMod // pmod,imodチャンク用の構造体(アライメントに注意) 10byte
# {
# 	unsigned short srcOper;      // モジュレーション元(MIDI CCやピッチベンドなど)
# 	unsigned short destOper;     // 操作するジェネレータID
# 	short modAmount;   // 操作するジェネレータ量
# 	unsigned short amtSrcOper;   // モジュレーション元その2(ピッチベンドレンジなど)
# 	unsigned short modTransOper; // 変化量は線形か？曲線か？
# };
# struct SFGen // pmod,imodチャンク用の構造体 4byte
# {
# 	unsigned short  genOper;
# 	short genAmount;
# };

# TODO 上3つを格納->ソート後に番号などを更新->書き込み
# TODO 削除対応のためサイズを更新するように（再帰的に書き込む関数でも用意する

def __parse(f):
    tag = f.read(4).decode("ascii")
    size = struct.unpack_from("<l", f.read(4))[0]
    start = f.tell()
    if tag == "RIFF":
        tmp = []
        form = f.read(4).decode("ascii")
        while f.tell() - start < size:
            tmp.append(__parse(f))
        return Riff(tag, size, form, tmp, f.name)
    if tag == "LIST":
        name = f.read(4).decode("ascii")
        ret = List(tag, size, name, start, [])
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
        return PhdrRoot(tag, size, start, phdrs)
    if tag == "pbag":
        pbags = []
        while f.tell() - start < size:
            d = struct.unpack_from("<HH", f.read(4))
            pbags.append(Pbag(*d))
        return PbagRoot(tag, size, start, pbags)
    if tag == "pmod":
        pmods = []
        while f.tell() - start < size:
            d = struct.unpack_from("<HHhHH", f.read(10))
            pmods.append(Pmod(*d))
        return PmodRoot(tag, size, start, pmods)
    if tag == "pgen":
        pgens = []
        while f.tell() - start < size:
            d = struct.unpack_from("<Hh", f.read(4))
            pgens.append(Pgen(*d))
        return PgenRoot(tag, size, start, pgens)
    f.seek(start + size)
    return Element(tag, size, start)


def read(fname):
    with open(fname, 'rb') as f:
        r = __parse(f)
        return r

def write(fname, riff):
    with open(fname, 'wb') as fo:
        with open(riff.fname, 'rb') as fi:
            riff._write(fi, fo)
