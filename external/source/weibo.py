# import utils.log as log
import requests
import json
from lxml import etree
import sys
import time
import random
from datetime import datetime

SOURCE_NAME = "weibo"

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36"
headers = {"User_Agent": user_agent}
DTFORMAT = "%Y-%m-%dT%H:%M:%S"

def string_to_int(string):
    """字符串转换为整数"""
    if isinstance(string, int):
        return string
    elif string.endswith("万+"):
        string = string[:-2] + "0000"
    elif string.endswith("万"):
        string = float(string[:-1]) * 10000
    elif string.endswith("亿"):
        string = float(string[:-1]) * 100000000
    return int(string)

def standardize_info(weibo):
    """标准化信息，去除乱码"""
    for k, v in weibo.items():
        if (
            "bool" not in str(type(v))
            and "int" not in str(type(v))
            and "list" not in str(type(v))
            and "long" not in str(type(v))
        ):
            weibo[k] = (
                v.replace("\u200b", "")
                .encode(sys.stdout.encoding, "ignore")
                .decode(sys.stdout.encoding)
            )
    return weibo

def standardize_date(created_at):
    """标准化微博发布时间"""
    if "刚刚" in created_at:
        ts = datetime.now()
    elif "分钟" in created_at:
        minute = created_at[: created_at.find("分钟")]
        minute = datetime.timedelta(minutes=int(minute))
        ts = datetime.now() - minute
    elif "小时" in created_at:
        hour = created_at[: created_at.find("小时")]
        hour = datetime.timedelta(hours=int(hour))
        ts = datetime.now() - hour
    elif "昨天" in created_at:
        day = datetime.timedelta(days=1)
        ts = datetime.now() - day
    else:
        created_at = created_at.replace("+0800 ", "")
        ts = datetime.strptime(created_at, "%c")

    created_at = ts.strftime(DTFORMAT)
    full_created_at = ts.strftime("%Y-%m-%d %H:%M:%S")
    return created_at, full_created_at

def get_location(selector):
    """获取微博发布位置"""
    location_icon = "timeline_card_small_location_default.png"
    span_list = selector.xpath("//span")
    location = ""
    for i, span in enumerate(span_list):
        if span.xpath("img/@src"):
            if location_icon in span.xpath("img/@src")[0]:
                location = span_list[i + 1].xpath("string(.)")
                break
    return location

def get_article_url(selector):
    """获取微博中头条文章的url"""
    article_url = ""
    text = selector.xpath("string(.)")
    if text.startswith("发布了头条文章"):
        url = selector.xpath("//a/@data-url")
        if url and url[0].startswith("http://t.cn"):
            article_url = url[0]
    return article_url

def get_pics(weibo_info):
    """获取微博原始图片url"""
    if weibo_info.get("pics"):
        pic_info = weibo_info["pics"]
        pic_list = [pic["large"]["url"] for pic in pic_info]
        pics = ",".join(pic_list)
    else:
        pics = ""
    return pics

def get_topics(selector):
    """获取参与的微博话题"""
    span_list = selector.xpath("//span[@class='surl-text']")
    topics = ""
    topic_list = []
    for span in span_list:
        text = span.xpath("string(.)")
        if len(text) > 2 and text[0] == "#" and text[-1] == "#":
            topic_list.append(text[1:-1])
    if topic_list:
        topics = ",".join(topic_list)
    return topics

def get_at_users(selector):
    """获取@用户"""
    a_list = selector.xpath("//a")
    at_users = ""
    at_list = []
    for a in a_list:
        if "@" + a.xpath("@href")[0][3:] == a.xpath("string(.)"):
            at_list.append(a.xpath("string(.)")[1:])
    if at_list:
        at_users = ",".join(at_list)
    return at_users

def get_long_weibo(id):
    """获取长微博"""
    for i in range(5):
        url = "https://m.weibo.cn/detail/%s" % id
        html = requests.get(url, headers=headers, verify=False, timeout=10).text
        html = html[html.find('"status":') :]
        html = html[: html.rfind('"call"')]
        html = html[: html.rfind(",")]
        html = "{" + html + "}"
        js = json.loads(html, strict=False)
        weibo_info = js.get("status")
        if weibo_info:
            weibo = parse_weibo(weibo_info)
            return weibo
        time.sleep(random.randint(6, 10))

def parse_weibo(weibo_info):
    weibo = {}
    if weibo_info["user"]:
        weibo["user_id"] = weibo_info["user"]["id"]
        weibo["screen_name"] = weibo_info["user"]["screen_name"]
    else:
        weibo["user_id"] = ""
        weibo["screen_name"] = ""
    weibo["id"] = int(weibo_info["id"])
    weibo["bid"] = weibo_info["bid"]
    text_body = weibo_info["text"]
    selector = etree.HTML(f"{text_body}<hr>" if text_body.isspace() else text_body)

    text_list = selector.xpath("//text()")
    # 若text_list中的某个字符串元素以 @ 或 # 开始，则将该元素与前后元素合并为新元素，否则会带来没有必要的换行
    text_list_modified = []
    for ele in range(len(text_list)):
        if ele > 0 and (text_list[ele-1].startswith(('@','#')) or text_list[ele].startswith(('@','#'))):
            text_list_modified[-1] += text_list[ele]
        else:
            text_list_modified.append(text_list[ele])

    weibo["text"] = "\n".join(text_list_modified)
    weibo["article_url"] = get_article_url(selector)
    weibo["pics"] = get_pics(weibo_info)
    weibo["location"] = get_location(selector)
    weibo["created_at"] = weibo_info["created_at"]
    weibo["source"] = weibo_info["source"]
    weibo["attitudes_count"] = string_to_int(
        weibo_info.get("attitudes_count", 0)
    )
    weibo["comments_count"] = string_to_int(
        weibo_info.get("comments_count", 0)
    )
    weibo["reposts_count"] = string_to_int(weibo_info.get("reposts_count", 0))
    weibo["topics"] = get_topics(selector)
    weibo["at_users"] = get_at_users(selector)
    return standardize_info(weibo)

def get_one_weibo(info):
    """获取一条微博的全部信息"""
    try:
        weibo_info = info["mblog"]
        weibo_id = weibo_info["id"]
        retweeted_status = weibo_info.get("retweeted_status")
        is_long = (
            True if weibo_info.get("pic_num") > 9 else weibo_info.get("isLongText")
        )
        if retweeted_status and retweeted_status.get("id"):  # 转发
            retweet_id = retweeted_status.get("id")
            is_long_retweet = retweeted_status.get("isLongText")
            if is_long:
                weibo = get_long_weibo(weibo_id)
                if not weibo:
                    weibo = parse_weibo(weibo_info)
            else:
                weibo = parse_weibo(weibo_info)
            if is_long_retweet:
                retweet = get_long_weibo(retweet_id)
                if not retweet:
                    retweet = parse_weibo(retweeted_status)
            else:
                retweet = parse_weibo(retweeted_status)
            (
                retweet["created_at"],
                retweet["full_created_at"],
            ) = standardize_date(retweeted_status["created_at"])
            weibo["retweet"] = retweet
        else:  # 原创
            if is_long:
                weibo = get_long_weibo(weibo_id)
                if not weibo:
                    weibo = parse_weibo(weibo_info)
            else:
                weibo = parse_weibo(weibo_info)
        weibo["created_at"], weibo["full_created_at"] = standardize_date(
            weibo_info["created_at"]
        )
        return weibo
    except Exception as e:
        raise e

def get_source(source):
    wb_uid = source["uid"]
    wb_req = requests.get("https://m.weibo.cn/api/container/getIndex?container_ext=profile_uid:{0}&containerid=230413{0}".format(wb_uid), headers=headers, timeout=10)

    wb_data_json = wb_req.json()

    weibos = wb_data_json["data"]["cards"]
    parsed_weibos = []
    for w in weibos:
        print()
        if w["card_type"] == 11:
            temp = w.get("card_group",[0])
            if len(temp) >= 1:
                w = temp[0] or w
            else:
                w = w
        if w["card_type"] == 9:
            wb = get_one_weibo(w)
            parsed_weibos.append(wb)

    parsed_weibos.sort(key=lambda x:x["created_at"],reverse=True)
    print(parsed_weibos)
    return json.dumps(parsed_weibos)
