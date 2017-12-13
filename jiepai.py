#! /usr/bin/env python
# -*- coding:utf-8 -*-
# Author:Ypp

from urllib.parse import urlencode
from requests.exceptions import RequestException
from json.decoder import JSONDecodeError
from bs4 import BeautifulSoup
import requests
import json, re, os
import pymongo
from hashlib import md5
from multiprocessing import Pool
from toutiao.config import *

client = pymongo.MongoClient(MONGO_URL,connect=False)
db = client[MONGO_DB]

# 设置请求头信息
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36"
}


def get_page_index(offset, keyword):
    """抓取索引页"""
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': 3,
        'from': 'gallery'
    }
    url = 'https://www.toutiao.com/search_content/?' + urlencode(data)
    response = requests.get(url=url, headers=headers)
    try:
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print("请求索引页错误")
        return None


def parse_page_index(index_html):
    """解析索引页"""
    try:
        index_data = json.loads(index_html)
        if index_data and 'data' in index_data.keys():
            for item in index_data.get('data'):
                # 取出详情页的url并返回
                yield item.get('article_url')
    except JSONDecodeError:
        pass


def get_page_detail(detail_url):
    """爬取详情页"""
    response = requests.get(url=detail_url, headers=headers)
    try:
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print("请求详情页错误", detail_url)
        return None


def parse_page_detail(detail_html, detail_url):
    """解析详情页"""
    soup = BeautifulSoup(detail_html, 'lxml')
    title = soup.select('title')[0].get_text()
    print(title)
    images_pattern = re.compile('gallery:\sJSON.parse\("(.*?)"\),', re.S)
    res = re.search(images_pattern, detail_html)
    if res:
        # 将json格式字符串的数据转换json对象
        detail_data = json.loads(re.sub('\\\\', '', res.group(1)))
        # print(detail_data)
        if detail_data and 'sub_images' in detail_data.keys():
            sub_images = detail_data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            # 调用方法下载图片到本地
            # for image in images:download_image(image)
            return {
                'title': title,
                'url': detail_url,
                'images': images
            }


def save_to_mongo(result):
    """存储到mongo数据库"""
    if db[MONGO_TABLE].insert(result):
        print("存储到MongoDB成功", result)
        return True
    return False


def download_image(image_url):
    """下载图片"""
    print("正在下载", image_url)
    response = requests.get(url=image_url, headers=headers)
    try:
        if response.status_code == 200:
            save_image(response.content)
        return None
    except RequestException:
        print("请求图片url错误", image_url)
        return None


def save_image(content):
    """下载图片"""
    file_path = '{0}{1}.{2}'.format(os.getcwd() + '/images/', md5(content).hexdigest(), 'jpg')
    # print(file_path)
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            f.write(content)
            f.close()


def main(offset):
    index_html = get_page_index(offset, KEYWORD)
    # 讲索引页传入函数解析并返回详情页的URL
    for detail_url in parse_page_index(index_html):
        # print(detail_url)
        detail_html = get_page_detail(detail_url)
        if detail_html:
            result = parse_page_detail(detail_html, detail_url)
            # 讲返回数据存储到MongoDB
            if result: save_to_mongo(result)
            # print(result)


if __name__ == '__main__':
    # main()
    groups = [x * 20 for x in range(GROUP_START, GROUP_END + 1)]
    # 采用多进程
    pool = Pool()
    pool.map(main, groups)
