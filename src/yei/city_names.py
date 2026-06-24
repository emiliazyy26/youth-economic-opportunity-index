"""Mapping between English city names and Chinese names commonly used by the NBS."""

CITY_NAME_ZH: dict[str, str] = {
    "Beijing": "北京",
    "Shanghai": "上海",
    "Shenzhen": "深圳",
    "Guangzhou": "广州",
    "Hangzhou": "杭州",
    "Nanjing": "南京",
    "Suzhou": "苏州",
    "Chengdu": "成都",
    "Wuhan": "武汉",
    "Xi'an": "西安",
    "Hefei": "合肥",
    "Changsha": "长沙",
    "Qingdao": "青岛",
    "Xiamen": "厦门",
    "Zhengzhou": "郑州",
    "Chongqing": "重庆",
    "Harbin": "哈尔滨",
    "Shenyang": "沈阳",
    "Kunming": "昆明",
    "Nanchang": "南昌",
}

CITY_NAME_EN = {zh: en for en, zh in CITY_NAME_ZH.items()}

# NBS city annual database regcode
CITY_REGCODE: dict[str, str] = {
    "Beijing": "110000",
    "Shanghai": "310000",
    "Shenzhen": "440300",
    "Guangzhou": "440100",
    "Hangzhou": "330100",
    "Nanjing": "320100",
    "Suzhou": "320500",
    "Chengdu": "510100",
    "Wuhan": "420100",
    "Xi'an": "610100",
    "Hefei": "340100",
    "Changsha": "430100",
    "Qingdao": "370200",
    "Xiamen": "350200",
    "Zhengzhou": "410100",
    "Chongqing": "500000",
    "Harbin": "230100",
    "Shenyang": "210100",
    "Kunming": "530100",
    "Nanchang": "360100",
}
