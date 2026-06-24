"""各城市统计公报列表页配置。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CommuniqueSource:
    city: str
    list_urls: tuple[str, ...]
    base_url: str


COMMUNIQUE_SOURCES: list[CommuniqueSource] = [
    CommuniqueSource(
        "Beijing",
        ("https://tjj.beijing.gov.cn/tjsj_31433/tjgb_31445/ndgb_31446/",),
        "https://tjj.beijing.gov.cn",
    ),
    CommuniqueSource(
        "Shanghai",
        ("https://tjj.sh.gov.cn/tjgb/index.html",),
        "https://tjj.sh.gov.cn",
    ),
    CommuniqueSource(
        "Shenzhen",
        ("https://tjj.sz.gov.cn/zwgk/zfxxgkml/tjsj/tjgb/",),
        "https://tjj.sz.gov.cn",
    ),
    CommuniqueSource(
        "Guangzhou",
        ("http://tjj.gz.gov.cn/stats_newtjyw/tjsj/tjgb/qstjgb/mindex.html",),
        "http://tjj.gz.gov.cn",
    ),
    CommuniqueSource(
        "Hangzhou",
        ("https://tjj.hangzhou.gov.cn/col/col1229025555/index.html",),
        "https://tjj.hangzhou.gov.cn",
    ),
    CommuniqueSource(
        "Nanjing",
        ("https://tjj.nanjing.gov.cn/bmfw/njsj/", "https://tjj.nanjing.gov.cn/bmfw/njsj/index_1.html"),
        "https://tjj.nanjing.gov.cn",
    ),
    CommuniqueSource(
        "Suzhou",
        ("http://tjj.suzhou.gov.cn/sztjj/tjgb/nav_list.shtml",),
        "http://tjj.suzhou.gov.cn",
    ),
    CommuniqueSource(
        "Chengdu",
        ("https://tjj.chengdu.gov.cn/tjgb/ndgb/", "https://cdstats.chengdu.gov.cn/tjgb/ndgb/index.shtml"),
        "https://tjj.chengdu.gov.cn",
    ),
    CommuniqueSource(
        "Wuhan",
        ("https://tjj.wuhan.gov.cn/tjfw/tjgb/",),
        "https://tjj.wuhan.gov.cn",
    ),
    CommuniqueSource(
        "Xi'an",
        ("https://tjj.xa.gov.cn/tjgb/ndgb/index.htm", "https://tjj.xa.gov.cn/tjgb/ndgb/"),
        "https://tjj.xa.gov.cn",
    ),
    CommuniqueSource(
        "Hefei",
        ("https://tjj.hefei.gov.cn/tjgb/ndgb/",),
        "https://tjj.hefei.gov.cn",
    ),
    CommuniqueSource(
        "Changsha",
        ("https://tjj.changsha.gov.cn/tjgb/ndgb/",),
        "https://tjj.changsha.gov.cn",
    ),
    CommuniqueSource(
        "Qingdao",
        ("https://tjj.qingdao.gov.cn/tjgb/ndgb/",),
        "https://tjj.qingdao.gov.cn",
    ),
    CommuniqueSource(
        "Xiamen",
        ("https://tjj.xm.gov.cn/tjgb/ndgb/",),
        "https://tjj.xm.gov.cn",
    ),
    CommuniqueSource(
        "Zhengzhou",
        ("https://tjj.zhengzhou.gov.cn/tjgb/index.jhtml",),
        "https://tjj.zhengzhou.gov.cn",
    ),
    CommuniqueSource(
        "Chongqing",
        (
            "http://tjj.cq.gov.cn/zwgk_233/fdzdgknr/tjxx/sjzl_55471/tjgb_55472/wap.html",
            "http://tjj.cq.gov.cn/zwgk_233/fdzdgknr/tjxx/sjzl_55471/tjgb_55472/index_1.html",
        ),
        "http://tjj.cq.gov.cn",
    ),
    CommuniqueSource(
        "Harbin",
        ("https://tjj.harbin.gov.cn/tjgb/ndgb/",),
        "https://tjj.harbin.gov.cn",
    ),
    CommuniqueSource(
        "Shenyang",
        ("http://tjj.shenyang.gov.cn/sjfb/tjgb/",),
        "http://tjj.shenyang.gov.cn",
    ),
    CommuniqueSource(
        "Kunming",
        ("https://www.km.gov.cn/", "https://tjj.km.gov.cn"),
        "https://www.km.gov.cn",
    ),
    CommuniqueSource(
        "Nanchang",
        ("https://tjj.nc.gov.cn/ncstjj/tjgb/nav_list.shtml",),
        "https://tjj.nc.gov.cn",
    ),
]

COMMUNIQUE_SOURCE_BY_CITY = {item.city: item for item in COMMUNIQUE_SOURCES}
