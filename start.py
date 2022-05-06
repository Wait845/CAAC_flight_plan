# -*- coding: UTF-8 -*-
import asyncio
import httpx
import json
import datetime
import time


# 接口URL
SEARCH_URL = "http://www.caac.gov.cn/caacgov/frontend/flight/plan/getlist.do"

# 境外城市
CITIES_OUT = ["万象", "东京", "东京成田", "亚的斯亚贝巴", "仰光", "伊斯兰堡", "伊斯坦布尔",
        "伦敦", "内罗毕", "利雅得", "加德满都", "华沙", "卡拉奇", "吉隆坡", "哥本哈根",
        "塔什干", "墨尔本", "墨西哥城", "多伦多", "多哈", "大邱", "大阪", "奥克兰",
        "巴库", "巴格达", "巴黎", "布鲁塞尔", "底特律", "开罗", "德里", "德黑兰",
        "悉尼", "斯德哥尔摩", "斯里巴加湾", "新加坡", "旧金山", "明斯克", "曼德勒",
        "曼谷", "沉阳", "河内", "法兰克福", "洛杉矶", "清莱", "清迈", "温哥华",
        "特拉维夫", "科伦坡", "科威特", "米兰", "约翰内斯堡", "纽约", "维也纳",
        "美娜多", "胡志明市", "芝加哥", "苏黎世", "莫斯科", "西哈努克", "西雅图",
        "赫尔辛基", "达卡", "达拉斯", "达累斯萨拉姆", "迪拜", "里斯本", "金边",
        "釜山", "阿姆斯特丹", "阿尔及尔", "阿布扎比", "阿拉木图", "雅典", "雅加达",
        "首尔","马尼拉","马德里","马斯喀特","马斯科特"]

# 境内城市
CITIES_IN = ["上海", "兰州", "北京", "南京", "南宁", "南昌", "厦门", "呼和浩特",
            "哈尔滨", "大兴", "大连", "天津", "太原", "威海", "宁波", "常州",
            "广州", "延吉", "德宏", "成都", "无锡", "昆明", "杭州", "武汉",
            "济南", "济州", "深圳", "烟台", "石家庄", "福州", "西双版纳",
            "西安", "郑州", "重庆", "长春", "长沙", "青岛"]

# 并发量(不要设太高，服务器很烂)
sem = asyncio.Semaphore(5)

all_flights = {}


async def parse_data(data: str) -> bool:
    """
    解析数据

    :param data: 待解析的数据
    :return: 是否有下一页
    """
    has_next = False

    # 判断是否获取成功
    data = json.loads(data)

    # 无效响应
    if not data.get("success", None):
        return has_next

    # 解析航班数据
    root = data.get("root", {})
    flitght_data = root.get("root", [])
    for flight in flitght_data:
        ori = flight["ori"]
        arr = flight["arr"]

        if not all_flights.get(ori, None):
            all_flights[ori] = {}
        if not all_flights[ori].get(arr, None):
            all_flights[ori][arr] = []

        all_flights[ori][arr].append(flight)

    # 判断是否有下一页
    total = root.get("total", 0)
    page = root.get("page", 1)
    current_size = page * 15
    if current_size < total:
        has_next = True
        return has_next

    return has_next


async def search(depart_city: str, arri_city: str, a_id: int):
    """
    查询航班

    :param depart_city: 出发城市
    :param arri_city: 到达城市
    :param a_id: 协程id
    """
    data = {
        "ori":depart_city,
        "arr": arri_city,
        "pageIndex": None,
        "pageSize": 15
    }

    async with sem:
        print("开始运行协程:", a_id)

        # 创建连接
        async with httpx.AsyncClient(timeout=30) as client:
            page = 1

            # 循环直到没有下一页
            while True:
                data["pageIndex"] = page
                status_code = 0

                # 请求失败的话则不断重试
                while status_code != 200:
                    print("STATUS_CODE:", status_code)
                    await asyncio.sleep(1)
                    try:
                        resp = await client.post(
                            url=SEARCH_URL,
                            data=data
                        )
                    except:
                        print("请求超时，超时数据:", data)
                        continue
                    status_code = resp.status_code

                # 解析数据
                result_parse = await parse_data(resp.text)

                # 是否存在下一页
                if not result_parse:
                    break
                else:
                    page += 1


if __name__ == "__main__":
    task_list = []
    count = 0
    for ori in CITIES_IN:
        for arr in CITIES_OUT:
            task_list.append(search(ori, arr, count))
            count += 1
            task_list.append(search(arr, ori, count))
            count += 1

    st = time.time()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(task_list))
    et = time.time()

    print(json.dumps(all_flights, ensure_ascii=False))
    print("用时:", et - st)
