#!/usr/bin/env python3
"""
创作工作台 - 自动采集与AI改写脚本
功能：
  1. 抓取抖音/全网热榜
  2. 用 AI 改写为贴合用户赛道的内容（10条选题灵感 + 10条二创角度）
  3. 推送到 GitHub Gist

使用方式：
  python3 fetch_and_generate.py

环境变量（必须设置）：
  GITHUB_TOKEN    - GitHub Personal Access Token（需要 gist 权限）
  GIST_ID         - 目标 Gist ID（创建后替换）
  NICHE_KEYWORDS  - 赛道关键词，多个用逗号分隔（如 "职场成长,副业赚钱,个人IP"）

可选环境变量：
  AI_API_KEY      - AI API Key（如 OpenAI/DeepSeek/通义千问）
  AI_API_BASE     - AI API Base URL（如 https://api.deepseek.com/v1）
  AI_MODEL        - AI 模型名（默认 gpt-4o-mini）
"""

import os
import sys
import json
import re
import hashlib
import time
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen, HTTPError
from urllib.parse import quote, urlencode
from urllib.error import URLError
import ssl

# ===== 配置 =====
# 中国时区
CST = timezone(timedelta(hours=8))
TODAY = datetime.now(CST).strftime('%Y-%m-%d')
TIMESTAMP = datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GIST_ID = os.environ.get('GIST_ID', '')
NICHE_KEYWORDS = os.environ.get('NICHE_KEYWORDS', '低卡健康菜,家常菜分享,减脂饮食')

AI_API_KEY = os.environ.get('AI_API_KEY', '')
AI_API_BASE = os.environ.get('AI_API_BASE', 'https://api.openai.com/v1')
AI_MODEL = os.environ.get('AI_MODEL', 'gpt-4o-mini')

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output.json')


def log(msg):
    """打印带时间戳的日志"""
    print(f"[{TIMESTAMP}] {msg}")


def fetch_json(url, headers=None, timeout=15):
    """通用 JSON 请求"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
    }
    if headers:
        default_headers.update(headers)
    req = Request(url, headers=default_headers)
    try:
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        log(f"  ⚠️ 请求失败 {url}: {e}")
        return None


def fetch_html(url, headers=None, timeout=15):
    """通用 HTML 请求"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
    }
    if headers:
        default_headers.update(headers)
    req = Request(url, headers=default_headers)
    try:
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        log(f"  ⚠️ 请求失败 {url}: {e}")
        return None


# ===== 热榜数据源 =====

def fetch_douyin_hot():
    """抓取抖音热榜（通过公开 API）"""
    log("抓取抖音热榜...")
    data = fetch_json('https://api.vvhan.com/api/hotlist/douyinHot')
    if data and data.get('success') and data.get('data'):
        items = []
        for item in data['data'][:20]:
            items.append({
                'title': item.get('title', ''),
                'hot': item.get('hot', 0),
                'url': item.get('url', '')
            })
        log(f"  ✅ 抖音热榜：获取 {len(items)} 条")
        return items
    # 备用源
    data2 = fetch_json('https://api.vvhan.com/api/hotlist/wbHot')
    if data2 and data2.get('success') and data2.get('data'):
        items = []
        for item in data2['data'][:20]:
            items.append({
                'title': item.get('title', ''),
                'hot': item.get('hot', 0),
                'url': item.get('url', '')
            })
        log(f"  ✅ 微博热榜（备用）：获取 {len(items)} 条")
        return items
    log("  ⚠️ 热榜抓取失败")
    return []


def fetch_weibo_hot():
    """抓取微博热搜"""
    log("抓取微博热搜...")
    data = fetch_json('https://api.vvhan.com/api/hotlist/wbHot')
    if data and data.get('success') and data.get('data'):
        items = []
        for item in data['data'][:20]:
            items.append({
                'title': item.get('title', ''),
                'hot': item.get('hot', 0),
                'url': item.get('url', '')
            })
        log(f"  ✅ 微博热搜：获取 {len(items)} 条")
        return items
    return []


def fetch_baidu_hot():
    """抓取百度热搜"""
    log("抓取百度热搜...")
    data = fetch_json('https://api.vvhan.com/api/hotlist/baiduHot')
    if data and data.get('success') and data.get('data'):
        items = []
        for item in data['data'][:20]:
            items.append({
                'title': item.get('title', ''),
                'hot': item.get('hot', 0),
                'url': item.get('url', '')
            })
        log(f"  ✅ 百度热搜：获取 {len(items)} 条")
        return items
    return []


def fetch_zhihu_hot():
    """抓取知乎热榜"""
    log("抓取知乎热榜...")
    data = fetch_json('https://api.vvhan.com/api/hotlist/zhihuHot')
    if data and data.get('success') and data.get('data'):
        items = []
        for item in data['data'][:15]:
            items.append({
                'title': item.get('title', ''),
                'hot': item.get('hot', 0),
                'url': item.get('url', '')
            })
        log(f"  ✅ 知乎热榜：获取 {len(items)} 条")
        return items
    return []


def merge_hot_lists():
    """合并多平台热榜并去重"""
    all_items = []
    all_items.extend(fetch_douyin_hot())
    all_items.extend(fetch_weibo_hot())
    all_items.extend(fetch_baidu_hot())
    all_items.extend(fetch_zhihu_hot())
    # 去重（按标题相似度）
    seen = set()
    unique = []
    for item in all_items:
        key = hashlib.md5(item['title'].encode()).hexdigest()[:8]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    # 按热度排序
    unique.sort(key=lambda x: x.get('hot', 0), reverse=True)
    log(f"🔥 合并去重后共 {len(unique)} 条热点")
    return unique[:30]


# ===== AI 改写 =====

def call_ai(prompt, max_tokens=4000):
    """调用 AI API 进行改写"""
    if not AI_API_KEY:
        log("  ⚠️ 未配置 AI API Key，跳过 AI 改写")
        return None

    log(f"  🤖 调用 AI ({AI_MODEL})...")
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        api_url = f"{AI_API_BASE.rstrip('/')}/chat/completions"
        body = json.dumps({
            "model": AI_MODEL,
            "messages": [
                {"role": "system", "content": "你是一个专业的自媒体内容策划师，擅长将热点事件和行业资讯改写为适合短视频创作的选题方案。输出格式必须严格是合法的 JSON。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.8
        }).encode('utf-8')

        req = Request(api_url, data=body, headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {AI_API_KEY}',
            'User-Agent': 'Mozilla/5.0'
        })

        with urlopen(req, timeout=60, context=ctx) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            content = result['choices'][0]['message']['content']
            # 提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
            return None
    except Exception as e:
        log(f"  ⚠️ AI 调用失败: {e}")
        return None


def generate_inspiration(hot_items):
    """用 AI 生成 10 条选题灵感"""
    log("💡 生成选题灵感...")

    hot_text = '\n'.join([f"{i+1}. {item['title']}" for i, item in enumerate(hot_items[:15])])

    prompt = f"""请根据以下今日全网热点，结合我的创作赛道「{NICHE_KEYWORDS}」，生成 10 条短视频选题灵感。

要求：
1. 每条包含：title（标题）、tags（3个标签数组）、desc（50-100字说明）、douyinKeyword（抖音搜索关键词）、biliKeyword（B站搜索关键词）
2. 选题要贴合热点但要有独特视角
3. 输出严格的 JSON 数组格式，不要多余文字

今日热点：
{hot_text}

赛道关键词：{NICHE_KEYWORDS}

请输出如下格式：
```json
[
  {{
    "title": "选题标题",
    "tags": ["标签1", "标签2", "标签3"],
    "desc": "选题说明，包含拍摄思路和核心卖点",
    "douyinKeyword": "抖音搜索词",
    "biliKeyword": "B站搜索词"
  }}
]
```"""

    result = call_ai(prompt)
    if result and isinstance(result, list):
        # 添加日期
        for item in result:
            item['date'] = TODAY
        log(f"  ✅ 生成 {len(result)} 条选题灵感")
        return result

    # AI 失败时用模板生成
    log("  ⚠️ AI 改写失败，使用模板生成")
    fallback = []
    for i, item in enumerate(hot_items[:10]):
        fallback.append({
            'title': f"热点解读：{item['title'][:20]}",
            'tags': ['热点', NICHE_KEYWORDS.split(',')[0].strip(), '日更'],
            'desc': f"结合今日热点「{item['title']}」，从{NICHE_KEYWORDS.split(',')[0].strip()}的角度进行解读，给出实用建议和独特观点。",
            'douyinKeyword': item['title'][:10],
            'biliKeyword': item['title'][:10] + ' 深度解读',
            'date': TODAY
        })
    return fallback


def generate_hot_video(hot_items):
    """用 AI 生成 10 条二创角度"""
    log("🔥 生成爆款二创角度...")

    hot_text = '\n'.join([f"{i+1}. {item['title']}" for i, item in enumerate(hot_items[:15])])

    prompt = f"""请根据以下今日全网热点，结合我的创作赛道「{NICHE_KEYWORDS}」，为每个热点给出 1 个短视频二创改编角度。

要求：
1. 每条包含：title（原热点标题）、angle（改编角度，50-100字）
2. 改编角度要具体：建议开头钩子、中间结构、结尾引导互动的方式
3. 输出严格的 JSON 数组格式，不要多余文字

今日热点：
{hot_text}

赛道关键词：{NICHE_KEYWORDS}

请输出如下格式：
```json
[
  {{
    "title": "原热点标题",
    "angle": "二创改编角度说明"
  }}
]
```"""

    result = call_ai(prompt)
    if result and isinstance(result, list):
        for item in result:
            item['date'] = TODAY
        log(f"  ✅ 生成 {len(result)} 条二创角度")
        return result

    # AI 失败时用模板生成
    log("  ⚠️ AI 改写失败，使用模板生成")
    fallback = []
    for i, item in enumerate(hot_items[:10]):
        fallback.append({
            'title': item['title'],
            'angle': f"🎤 开头用「你知道吗，{item['title'][:15]}背后还有个秘密」做钩子 → 中间从{NICHE_KEYWORDS.split(',')[0].strip()}视角拆解 → 结尾引导评论「你遇到过吗？»",
            'date': TODAY
        })
    return fallback


# ===== GitHub Gist 操作 =====

def push_to_gist(data):
    """推送数据到 GitHub Gist"""
    if not GITHUB_TOKEN or GITHUB_ID == 'YOUR_GIST_ID':
        log("⚠️ 未配置 GIST_ID，数据将保存到本地文件")
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"✅ 数据已保存到 {OUTPUT_FILE}")
        return False

    log(f"📤 推送数据到 Gist ({GIST_ID})...")
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        gist_url = f"https://api.github.com/gists/{GIST_ID}"
        body = json.dumps({
            "description": f"创作工作台数据 - 更新于 {TIMESTAMP}",
            "public": True,
            "files": {
                "data.json": {
                    "content": json.dumps(data, ensure_ascii=False, indent=2)
                }
            }
        }).encode('utf-8')

        req = Request(gist_url, data=body, method='PATCH', headers={
            'Authorization': f'token {GITHUB_TOKEN}',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0'
        })

        with urlopen(req, timeout=30, context=ctx) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            raw_url = result.get('files', {}).get('data.json', {}).get('raw_url', '')
            log(f"✅ 推送成功！")
            log(f"   Raw URL: {raw_url}")
            return True

    except Exception as e:
        log(f"⚠️ Gist 推送失败: {e}")
        # 保存到本地
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"✅ 数据已保存到本地文件 {OUTPUT_FILE}")
        return False


# ===== 主流程 =====

def main():
    log("=" * 50)
    log("🚀 创作工作台 - 自动采集与生成")
    log(f"📅 日期: {TODAY}")
    log(f"🏷️  赛道: {NICHE_KEYWORDS}")
    log("=" * 50)

    # 1. 抓取热榜
    hot_items = merge_hot_lists()
    if not hot_items:
        log("❌ 未获取到任何热点数据，终止运行")
        sys.exit(1)

    # 2. AI 改写
    inspiration = generate_inspiration(hot_items)
    hot_video = generate_hot_video(hot_items)

    # 3. 组装数据
    output_data = {
        "updatedAt": TIMESTAMP,
        "date": TODAY,
        "niche": NICHE_KEYWORDS,
        "inspiration": inspiration[:10],
        "hotVideo": hot_video[:10],
        "sourceHotList": hot_items[:20]
    }

    # 4. 推送到 Gist
    success = push_to_gist(output_data)

    # 5. 输出摘要
    log("=" * 50)
    log("📊 本次生成摘要：")
    log(f"   选题灵感: {len(inspiration)} 条")
    log(f"   二创角度: {len(hot_video)} 条")
    if success:
        log("✅ 全部完成，数据已推送到 Gist！")
    else:
        log("✅ 全部完成，数据已保存到本地！")
    log("=" * 50)


if __name__ == '__main__':
    main()
