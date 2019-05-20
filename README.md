# sf2conv

設定ファイル書式
{
    "imd":{
        "map":[
            {
                "name":"NAME",
            },
            {
                "name":"NAME",
                "program_start":0,
                "program_end":11
            },
        ]
    },
    "inst_name_table":{
        "Acoustic":"A",
        "Electoric":"E",
    }
    "dst":"dst_folder",
    "dst_host_path":"dst_host_path",
    "src":[
        {
            "sf2_name":"sample.sf2",
            "suffix":"SP",
            "defaul_bank":0,
            "imd_drum_map":"SP Dr",
            "imd_inst_map_mode":"auto",
            "exclude":[
                "bank/program", "0/5"
            ],
            "custom_drums":[
                "bank/program", "0/4"
            ],
            "inst_name_table":{
                "SampleInst_":"",
                "HardElectPin":"HardEP",
            }
        },
        {
            "sf2_name":"SQUARE.sf2",
            "suffix":"SQ",
            "defaul_bank":1,
            "imd_drum_map":"OTHER",
            "imd_inst_map_mode":"custom",
            "imd_inst_map_name":"SQUARE",
        }
    ]
}
