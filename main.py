import riff
import sys
import csv
import codecs


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

def save_table(inst, drum, dst):
    with open(dst, 'w') as f:
        f.write("INST\n")
        for pn, t in inst.items():
            f.write(f"{pn}\n")
            for bn, n in sorted(t.items(), key=lambda x:x[0]):
                f.write(f"-{bn}:{n}\n")
        f.write("DRUM\n")
        for bn, n in sorted(drum.items(), key=lambda x:x[0]):
            f.write(f"{bn}:{n}\n")
                
def save_vmssf(sf2_table, dst):
    with open(dst, 'w') as f:
        f.write("[SoundFonts]\n")
        for n, i in zip(sf2_table, range(1, len(sf2_table)+1)):
            f.write(f"sf{i}={n}\n")
            f.write(f"sf{i}.enabled=1\n")
            f.write(f"sf{i}.preload=0\n")

def save_imd_inst(inst, dst):
    table = [
        [0, 7, "Map1", "ピアノ"],
        [8, 15, "Map2", "クロマチック・パーカッション"],
        [16, 23, "Map3", "オルガン"],
        [24, 31, "Map4", "ギター"], 
        [32, 39, "Map5", "ベース"],
        [40, 47, "Map6", "ストリングス"],
        [48, 55, "Map7", "アンサンブル"],
        [56, 63, "Map8", "ブラス"],
        [64, 71, "Map9", "リード"],
        [72, 79, "Map10", "パイプ"],
        [80, 87, "Map11", "シンセリード"],
        [88, 95, "Map12", "シンセパッド"],
        [96, 103, "Map13", "シンセSFX"],
        [104, 111, "Map14", "エスニック"],
        [112, 119, "Map15", "パーカッシブ"],
        [120, 127, "Map16", "SFX"]
    ]
    with codecs.open(dst, 'w', 'shift_jis') as f:
        f.write("[IMD]\n")
        f.write("Name=SF2Main\n")
        for t, i in zip(table, range(len(table))):
            f.write(f"{i}={t[2]}\n")
        f.write("\n")
            
        for t in table:
            f.write(f"[{t[2]}]\n")
            f.write(f"Name={t[3]}\n")
            i = 0
            for pn in range(t[0], t[1]+1):
                if not pn in inst:
                    continue
                for bn, n in sorted(inst[pn].items(), key=lambda x:x[0]):
                    f.write(f"{i}=N,{bn},0,{pn},{pn+1}-{bn}:{n}\n")
                    i += 1
            f.write("\n")

def save_imd_drum(drum, imd_table, imd_keys, dst):
    with open(dst, 'w') as f:
        f.write("[IMD]\n")
        f.write("Name=SF2Main Drum set\n")
        for n, i in zip(imd_keys, range(len(imd_keys))):
            f.write(f"{i}={n}\n")
        f.write("\n")
        for k in imd_keys:
            f.write(f"[{k}]\n")
            f.write(f"Name={k}\n")
            i = 0
            imd_table[k].sort()
            for pn in imd_table[k]:
                f.write(f"{i}=N,0,0,{pn},Dr:{drum[pn]}\n")
                i += 1
            f.write("\n")

def main():
    conf = sys.argv[1]
    src_dir = sys.argv[2]
    dst_dir = sys.argv[3]
    host_root_path = sys.argv[4]
    sf2_table = []
    # 音色テーブル [program number][bank]
    inst_table = {}
    for i in range(128):
        inst_table[i] = {}
    # ドラムテーブル(bank=128)
    drum_table = {}
    drum_imd_table = {}
    drum_imd_keys = []
    with open(conf, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            sf2_name = row[0]
            sf2_table.append(f"{host_root_path}\{sf2_name}")
            suffix = row[1]
            if len(suffix) != 0:
                suffix = f"[{suffix}]"
            bank = int(row[2])
            drum_imd_key = row[3]
            black_list = row[4:]
            
            sf2 = riff.read(f"{src_dir}/{sf2_name}")
            phdr_root = sf2.phdr()
            phdr_root.sort()
            for i in phdr_root.data[:]:
                if i.key() in black_list:
                    phdr_root.data.remove(i)
                    continue
                if i.name == "EOP":
                    continue
                if i.bank == 128:
                    idx = getFreeIndex(drum_table, i.presentno)
                    if idx is None:
                        phdr_root.data.remove(i)
                        continue
                    drum_table[idx] = f"{i.name}{suffix}"
                    if not drum_imd_key in drum_imd_table:
                        drum_imd_keys.append(drum_imd_key)
                        drum_imd_table[drum_imd_key] = []
                    drum_imd_table[drum_imd_key].append(idx)
                    i.presentno = idx
                else:
                    idx = getFreeIndex(inst_table[i.presentno], i.bank, bank)
                    if idx is None:
                        phdr_root.data.remove(i)
                        continue
                    inst_table[i.presentno][idx] = f"{i.name}{suffix}"
                    i.bank = idx
            riff.write(f"{dst_dir}/{sf2_name}", sf2)
    save_table(inst_table, drum_table, f"{dst_dir}/table.txt")
    save_vmssf(sf2_table, f"{dst_dir}/SF2Main.vmssf")
    save_imd_inst(inst_table, f"{dst_dir}/SF2Main.imd")
    save_imd_drum(drum_table, drum_imd_table, drum_imd_keys, f"{dst_dir}/SF2MainDrum.imd")
# self.name = name
# self.presentno = presentno
# self.bank = bank
# f = riff.read("test.sf2")
# riff.write("o.sf2", f)
# print(f)
# print(riff.read("o.sf2"))
main()
