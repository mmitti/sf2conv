import riff
import sys
import json
import codecs
import os
import re
from functools import cmp_to_key
from collections import OrderedDict


def t(table, key, default=None):
    if key in table:
        return table[key]
    return default


def getFreeIndex(t, no, default=None):
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
    # program number, bank, map_name(None=Auto), name, src_bank, src_name
    with open(dst, 'w') as f:
        f.write("IMD,ProgamNumber,Bank,Map,Name,SF2Key,SF2Name,Suffix\n")
        for i in inst:
            f.write("INST,"+",".join([str(j) for j in i]) + "\n")
        for i in drum:
            f.write("DRUM,"+",".join([str(j) for j in i]) + "\n")
    print(f"INST MAP TABLE {dst}")

def save_vmssf(sf2_table, dst):
    with open(dst, 'w') as f:
        f.write("[SoundFonts]\n")
        for n, i in zip(sf2_table, range(1, len(sf2_table)+1)):
            f.write(f"sf{i}={n}\n")
            f.write(f"sf{i}.enabled=1\n")
            f.write(f"sf{i}.preload=0\n")
    print(f"VMSSF FILE {dst}")

def save_imd_inst(inst, imd_map, dst):
    table = OrderedDict()
    key_map = {}
    for i in imd_map:
        table[i["name"]] = []
    for i in inst:
        if i[2] not in table:
            table[i[2]] = []
        table[i[2]].append(i)

    with codecs.open(dst, 'w', 'shift_jis') as f:
        f.write("[IMD]\n")
        f.write("Name=SF2Main\n")
        for k, i in zip(table.keys(), range(len(table.keys()))):
            key_map[k] = f"MAP{i+1}"
            f.write(f"{i}={key_map[k]}\n")
        f.write("\n")
        for k, e in table.items():
            f.write(f"[{key_map[k]}]\n")
            f.write(f"Name={k}\n")
            idx = 0
            for i in e:
                bn = i[1]
                pn = i[0]
                n = i[3]
                f.write(f"{idx}=N,{bn},0,{pn},{pn+1}-{bn}:{n}\n")
                idx += 1
            f.write("\n")
    print(f"IMD FILE {dst}")

def save_imd_drum(drum, order_table, dst):
    table = OrderedDict()
    for i in order_table:
        if i not in table:
            table[i] = []
    for i in drum:
        if i[2] not in table:
            table[i[2]] = []
        table[i[2]].append(i)

    with open(dst, 'w') as f:
        f.write("[IMD]\n")
        f.write("Name=SF2Main Drum set\n")
        for k, i in zip(table.keys(), range(len(table.keys()))):
            f.write(f"{i}={k}\n")
        f.write("\n")
        for k, e in table.items():
            f.write(f"[{k}]\n")
            f.write(f"Name={k}\n")
            idx = 0
            for i in e:
                bn = i[1]
                if bn == 128:
                    bn = 0
                pn = i[0]
                n = i[3]
                f.write(f"{idx}=N,{bn},0,{pn},Dr.:{n}\n")
                idx += 1
            f.write("\n")
    print(f"IMD FILE FOR DRUM {dst}")

def convert_name(table, name, max_len, custom_table={}):
    for k, v in custom_table.items():
        name = re.sub(f"{k}", v,  name)
    r = r'(?!([a-z] +[a-z])|([A-Z] +[A-Z])|([\d] +[\d]))(?P<c1>.) +(?P<c2>.)'
    name = re.sub(r, "\g<c1>\g<c2>", name)
    for k, v in table.items():
        name = re.sub(r, "\g<c1>\g<c2>", name)
        if len(name) <= max_len:
            return name
        name = name.replace(k, f"{v}.")
    return name


def imd_list_cmp(a, b):
    if a[0] == b[0]:
        if a[1] == b[1]:
            return 0
        return -1 if a[1] < b[1] else 1
    return -1 if a[0] < b[0] else 1
    
def load_json(path):
    with open(path) as f:
        r = f.readlines()
        json_str = ""
        for s in r:
            if s.strip().startswith("//"):
                continue
            json_str += s + "\n"
        return json.loads(json_str)


def main():
    conf_path = sys.argv[1]
    dry_run = False
    if len(sys.argv) == 3:
        dry_run = sys.argv[2] == "--dry_run"
        print("===DRY RUN===")
    conf = load_json(conf_path)
    src_dir = os.path.dirname(conf_path)
    dst_dir = conf["dst"]
    host_root_path = conf["dst_host_path"]
    name_len = int(conf["inst_name_max_len"])
    name_table = conf["inst_name_table"]
    imd_map = conf["imd"]["map"]
    # SoundFile List
    sf2_table = []
    # 音色テーブル [program number][bank]
    inst_table = {}
    for i in range(129):
        inst_table[i] = {}
    # imd用データ(program number, bank, map_name(None=Auto), name, src_bank, src_name, suffix)
    imd_inst_list = []
    imd_drum_list = []
    # ドラムの順番を保持するリスト
    imd_dram_order = []

    for s in conf["src"]:
        sf2_name = s["sf2_name"]
        sf2_table.append(f"{host_root_path}\{sf2_name}")
        suffix = s["suffix"]
        if len(suffix) != 0:
            suffix = f"[{suffix}]"
        bank = s["default_bank"]

        sf2 = riff.read(f"{src_dir}/{sf2_name}")
        phdr_root = sf2.phdr()
        # phdr_root.sort()
        imd_dram_order.append(s["imd_drum_map"])
        inst_name_custom_table = t(s, "inst_name_table", {})
        for i in phdr_root.data[:]:
            if i.key() in t(s, "exclude", []):
                # phdr_root.data.remove(i)
                continue
            if i.name == "EOP":
                continue

            if i.bank == 128 or i.key() in t(s, "custom_drums", []):
                idx = getFreeIndex(inst_table[i.presentno], i.bank)
                target_map = imd_drum_list
                default_map_name = s["imd_drum_map"]
            else:
                idx = getFreeIndex(inst_table[i.presentno], i.bank, bank)
                target_map = imd_inst_list
                default_map_name = t(s, "imd_inst_map_name")
            if default_map_name is None:
                for m in imd_map:
                    if not "program_start" in m or not "program_end" in m:
                        continue
                    if m["program_start"] <= i.presentno and i.presentno <= m["program_end"]:
                        default_map_name = m["name"]
            if idx is None:
                # phdr_root.data.remove(i)
                continue

            name = f"{convert_name(name_table, i.name, name_len, inst_name_custom_table)}{suffix}"
            target_map.append(
                (i.presentno, idx, default_map_name, name, i.key(), i.name, suffix))
            inst_table[i.presentno][idx] = name
            # TODO ドラムでbank=127の時動作するか、0と128は同じ扱いになる気がするので重複管理を修正
            i.bank = idx
        if not dry_run:
            print(f"SF2 FILE UPDATE {dst_dir}/{sf2_name}")
            riff.write(f"{dst_dir}/{sf2_name}", sf2)
    imd_inst_list = sorted(imd_inst_list, key=cmp_to_key(imd_list_cmp))
    imd_drum_list = sorted(imd_drum_list, key=cmp_to_key(imd_list_cmp))
    
    save_table(imd_inst_list, imd_drum_list, f"{dst_dir}/table.csv")
    if not dry_run:
        save_vmssf(sf2_table, f"{dst_dir}/SF2Main.vmssf")
        save_imd_inst(imd_inst_list, imd_map, f"{dst_dir}/SF2Main.imd")
        save_imd_drum(imd_drum_list, imd_dram_order, f"{dst_dir}/SF2MainDrum.imd")

main()
