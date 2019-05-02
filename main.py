import riff
import sys
import csv

def getFreeIndex(t, no, default = None):
    if default is not None:
        no = default
    if not no in t:
        return no
    for i in range(no, 128):
        if not i in t:
            return i
    for i in range(no, -1, -1):
        if not i in t:
            return i
    return None

def main():
    conf = sys.argv[1]
    src_dir = sys.argv[2]
    dst_dir = sys.argv[3]
    # 音色テーブル [program number][bank]
    merody_table = {}
    for i in range(128):
        merody_table[i] = {}
    # ドラムテーブル(bank=128)
    drum_table = {}
    with open(conf, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            sf2_name = row[0]
            suffix = row[1]
            if len(suffix) != 0:
                suffix = f"[{suffix}]"
            bank = int(row[2])
            sf2 = riff.read(f"{src_dir}/{sf2_name}")
            for i in sf2.phdr():
                print(i)
                if i.presentno == 255:
                    continue
                if i.bank == 128:
                    idx = getFreeIndex(drum_table, i.presentno)
                    if idx is None:
                        # todo remove
                        assert(False)
                        continue
                    drum_table[idx] = f"{i.name}{suffix}"
                    i.presentno = idx
                else:
                    idx = getFreeIndex(merody_table[i.presentno], i.bank, bank)
                    if idx is None:
                        assert(False)
                        continue
                    merody_table[i.presentno][idx] = f"{i.name}{suffix}"
                    i.bank = idx
            riff.write(f"{dst_dir}/{sf2_name}", sf2)
    # TODO imd
    print("INST")
    for pn, t in merody_table.items():
        print(pn)
        for bn, n in sorted(t.items(), key=lambda x:x[0]):
            print(f"-{bn}:{n}")
    print("DRUM")
    for bn, n in sorted(drum_table.items(), key=lambda x:x[0]):
        print(f"{bn}:{n}")
# self.name = name
# self.presentno = presentno
# self.bank = bank
# f = riff.read("test.sf2")
# riff.write("o.sf2", f)
# print(f)
# print(riff.read("o.sf2"))
main()
