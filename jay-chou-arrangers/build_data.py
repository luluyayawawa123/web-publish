import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from bs4 import BeautifulSoup

try:
    from opencc import OpenCC
except ImportError:  # pragma: no cover - optional local dependency
    for site_packages in Path(__file__).resolve().parent.glob(".venv/lib/python*/site-packages"):
        if str(site_packages) not in sys.path:
            sys.path.append(str(site_packages))
    try:
        from opencc import OpenCC
    except ImportError:
        OpenCC = None


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "data.js"
OPENCC = OpenCC("t2s") if OpenCC else None

ALBUMS = [
    {
        "album": "杰伦",
        "query_title": "杰倫 (專輯)",
        "release_date": "2000-11-07",
        "year": 2000,
    },
    {
        "album": "范特西",
        "query_title": "范特西",
        "release_date": "2001-09-14",
        "year": 2001,
    },
    {
        "album": "八度空间",
        "query_title": "八度空間 (專輯)",
        "release_date": "2002-07-18",
        "year": 2002,
    },
    {
        "album": "叶惠美",
        "query_title": "葉惠美",
        "release_date": "2003-07-31",
        "year": 2003,
    },
    {
        "album": "七里香",
        "query_title": "七里香 (專輯)",
        "release_date": "2004-08-03",
        "year": 2004,
    },
    {
        "album": "11月的肖邦",
        "query_title": "11月的蕭邦",
        "release_date": "2005-11-01",
        "year": 2005,
    },
    {
        "album": "依然范特西",
        "query_title": "依然范特西",
        "release_date": "2006-09-05",
        "year": 2006,
    },
    {
        "album": "我很忙",
        "query_title": "我很忙",
        "release_date": "2007-11-01",
        "year": 2007,
    },
    {
        "album": "魔杰座",
        "query_title": "魔杰座",
        "release_date": "2008-10-14",
        "year": 2008,
    },
    {
        "album": "跨时代",
        "query_title": "跨時代",
        "release_date": "2010-05-18",
        "year": 2010,
    },
    {
        "album": "惊叹号",
        "query_title": "驚嘆號 (專輯)",
        "release_date": "2011-11-11",
        "year": 2011,
    },
    {
        "album": "12新作",
        "query_title": "12新作",
        "release_date": "2012-12-28",
        "year": 2012,
    },
    {
        "album": "哎呦，不错哦",
        "query_title": "哎呦，不錯哦",
        "release_date": "2014-12-26",
        "year": 2014,
    },
    {
        "album": "周杰伦的床边故事",
        "query_title": "周杰倫的床邊故事",
        "release_date": "2016-06-24",
        "year": 2016,
    },
    {
        "album": "最伟大的作品",
        "query_title": "最伟大的作品",
        "release_date": "2022-07-15",
        "year": 2022,
    },
    {
        "album": "太阳之子",
        "query_title": "太陽之子 (專輯)",
        "release_date": "2026-03-25",
        "year": 2026,
        "release_note": "2026-03-24 先公开 MV 并开启实体预售，2026-03-25 数字专辑正式上线。",
    },
]

ARRANGER_NOTES = {
    "林迈可": {
        "signature": "Band 感、吉他线条、R&B 与抒情平衡",
        "profile": "常把周杰伦旋律做得更流畅、更像“会长期循环播放”的主流金曲，兼顾律动和情绪推进。",
        "keywords": ["流畅", "耐听", "吉他", "R&B", "抒情"],
        "representative": ["爱在西元前", "简单爱", "夜曲", "千里之外", "彩虹", "给我一首歌的时间"],
    },
    "钟兴民": {
        "signature": "大编制、戏剧张力、中国风与史诗感",
        "profile": "钟兴民的编曲常带有更强的空间感和镜头感，鼓点、弦乐、民族乐器与和声层次都更厚。",
        "keywords": ["史诗", "戏剧", "中国风", "弦乐", "空间感"],
        "representative": ["安静", "七里香", "青花瓷", "兰亭序", "菊花台", "双截棍"],
    },
    "黄雨勋": {
        "signature": "后期主力、色彩鲜明、流行与复古质感并行",
        "profile": "进入后期阶段后，黄雨勋几乎承包了大量关键作品，常把复古、拉丁、华丽铜管和现代流行包装在一起。",
        "keywords": ["复古", "华丽", "流行", "拉丁", "后期主力"],
        "representative": ["稻香", "Mojito", "最偉大的作品", "紅顏如霜", "床邊故事", "太陽之子"],
    },
    "洪敬尧": {
        "signature": "怪奇、剧场感、世界音乐与实验色彩",
        "profile": "洪敬尧参与的作品常更大胆，喜欢把戏剧性的段落、奇趣音色和跨文化元素拧在一起。",
        "keywords": ["实验", "奇想", "剧场", "世界音乐", "反差"],
        "representative": ["完美主义", "开不了口", "威廉古堡", "以父之名", "我的地盘", "藍色風暴"],
    },
    "周杰伦": {
        "signature": "作者本人视角、demo 感与节奏灵感最直接",
        "profile": "由周杰伦亲自编曲的歌，往往保留更直接的作者手感，节奏趣味与旋律落点更像原始灵感形态。",
        "keywords": ["作者性", "直接", "律动", "demo 感", "个人化"],
        "representative": ["可爱女人", "娘子", "阳光宅男", "四季列車", "止战之殇", "反方向的鐘"],
    },
    "蔡科俊": {
        "signature": "乐队现场感、吉他前置、青春速度感",
        "profile": "蔡科俊的编曲通常更强调乐器冲劲和 live band 的推进力，适合热血、速度感或摇滚向作品。",
        "keywords": ["现场感", "摇滚", "吉他", "速度感", "青春"],
        "representative": ["一路向北", "流浪诗人", "困兽之斗", "白色風車", "免費教學錄影帶", "愛的飛行日記"],
    },
    "派伟俊": {
        "signature": "新生代联编、电子流行与都市节奏",
        "profile": "近年的派伟俊更像是把周杰伦的旋律写法接到更新的电子和都市流行语境里，联编特征明显。",
        "keywords": ["电子", "都市", "新生代", "联编", "节奏"],
        "representative": ["I Do", "七月的極光", "愛琴海", "淘金小鎮", "聖徒", "誰稀罕"],
    },
    "陈思翰": {
        "signature": "单曲型协作、现代流行打磨",
        "profile": "出现次数不多，但可以看到更直接的现代流行编配思路，强调旋律抛点与节奏整洁度。",
        "keywords": ["现代流行", "整洁", "旋律抛点"],
        "representative": ["不爱我就拉倒"],
    },
    "吕尚霖": {
        "signature": "近年联编、细节型电子铺陈",
        "profile": "主要出现在《太阳之子》阶段的联编名单里，负责把新音色和律动细节再往前推一步。",
        "keywords": ["联编", "电子", "细节", "新音色"],
        "representative": ["谁稀罕", "I Do", "淘金小镇"],
    },
    "蒋希谦": {
        "signature": "辅助联编、氛围感点缀",
        "profile": "作品数量不多，但能看出偏向补足氛围层和织体细节的角色。",
        "keywords": ["氛围", "织体", "联编"],
        "representative": ["爱琴海"],
    },
    "Max Aidan": {
        "signature": "国际化协作、电子氛围补色",
        "profile": "在近年联编里提供更国际化的电子音色与氛围层，属于新阶段的合作拼图之一。",
        "keywords": ["国际化", "电子", "氛围", "联编"],
        "representative": ["七月的极光"],
    },
}

NAME_MAP = {
    "林邁可": "林迈可",
    "林迈可": "林迈可",
    "Michael Lin": "林迈可",
    "鐘興民": "钟兴民",
    "鍾興民": "钟兴民",
    "钟兴民": "钟兴民",
    "洪敬堯": "洪敬尧",
    "洪敬尧": "洪敬尧",
    "黃雨勳": "黄雨勋",
    "黃雨勛": "黄雨勋",
    "黃雨勋": "黄雨勋",
    "黄雨勳": "黄雨勋",
    "黄雨勛": "黄雨勋",
    "黄雨勋": "黄雨勋",
    "周杰倫": "周杰伦",
    "周杰伦": "周杰伦",
    "蔡科俊Again": "蔡科俊",
    "蔡科俊 Again": "蔡科俊",
    "蔡科俊": "蔡科俊",
    "派偉俊": "派伟俊",
    "派伟俊": "派伟俊",
    "呂尚霖": "吕尚霖",
    "吕尚霖": "吕尚霖",
    "蔣希謙": "蒋希谦",
    "蒋希谦": "蒋希谦",
    "陳思翰": "陈思翰",
    "陈思翰": "陈思翰",
    "Max Aidan": "Max Aidan",
}


def request_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


@lru_cache(maxsize=None)
def resolve_title(title: str) -> str:
    url = (
        "https://zh.wikipedia.org/w/api.php?action=query&redirects=1&format=json&titles="
        + urllib.parse.quote(title)
    )
    data = request_json(url)
    page = next(iter(data["query"]["pages"].values()))
    if "missing" in page:
        raise RuntimeError(f"Missing page title: {title}")
    return page["title"]


def fetch_page_html(title: str) -> BeautifulSoup:
    canonical = resolve_title(title)
    url = (
        "https://zh.wikipedia.org/w/api.php?action=parse&prop=text&format=json&page="
        + urllib.parse.quote(canonical)
    )
    last_error = None
    for _ in range(3):
        data = request_json(url)
        if "parse" in data:
            return BeautifulSoup(data["parse"]["text"]["*"], "lxml")
        last_error = data
        time.sleep(1)
    raise RuntimeError(f"Unable to parse {canonical}: {last_error}")


def page_url(title: str) -> str:
    canonical = resolve_title(title)
    return "https://zh.wikipedia.org/wiki/" + urllib.parse.quote(canonical.replace(" ", "_"))


def clean_title_cell(cell) -> str:
    strings = [text.strip() for text in cell.stripped_strings if text.strip()]
    if not strings:
        return ""
    title = strings[0].replace("（", "(").replace("）", ")")
    title = re.sub(r"\s+", " ", title).strip()
    for marker in (" 电影", " 電影", " 片尾曲", " 主题曲", " 主題曲", " 演唱："):
        if marker in title:
            title = title.split(marker, 1)[0].strip()
    return title


def to_simplified(value):
    if isinstance(value, str):
        return OPENCC.convert(value) if OPENCC else value
    if isinstance(value, list):
        return [to_simplified(item) for item in value]
    if isinstance(value, dict):
        return {key: to_simplified(item) for key, item in value.items()}
    return value


def normalize_name(name: str) -> str:
    normalized = " ".join(name.split()).strip(" ,，;；|")
    return NAME_MAP.get(normalized, normalized)


def split_arrangers(raw_text: str) -> list[str]:
    text = (
        raw_text.replace("、", "\n")
        .replace("/", "\n")
        .replace("／", "\n")
        .replace("&", "\n")
        .replace("＋", "\n")
    )
    names = []
    for item in re.split(r"[\n]+", text):
        normalized = normalize_name(item)
        if normalized:
            names.append(normalized)
    return names


def pick_track_table(soup: BeautifulSoup):
    for table in soup.find_all("table"):
        classes = table.get("class", [])
        headers = [th.get_text(" ", strip=True) for th in table.find_all("th")[:8]]
        joined = " ".join(headers)
        if ("tracklist" in classes or "曲序" in joined or "曲目名稱" in joined) and "DVD" not in joined and "VCD" not in joined:
            return table
    raise RuntimeError("Track table not found")


def extract_cover_url(soup: BeautifulSoup) -> str | None:
    image = soup.select_one("table.infobox img")
    if not image or not image.get("src"):
        return None
    src = image["src"]
    if src.startswith("//"):
        return "https:" + src
    return src


def extract_tracks(album_meta: dict) -> dict:
    canonical_title = resolve_title(album_meta["query_title"])
    soup = fetch_page_html(album_meta["query_title"])
    table = pick_track_table(soup)
    tracks = []
    header = []

    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"])
        cell_texts = [cell.get_text(" ", strip=True) for cell in cells]
        if not cell_texts:
            continue

        if any(
            label in cell_texts
            for label in ("曲序", "曲目", "曲目名稱", "词曲及编曲作者", "詞曲及編曲作者", "编曲", "編曲")
        ):
            header = cell_texts
            continue

        if not header or not cell_texts[0].rstrip(".").isdigit():
            continue

        if "詞曲及編曲作者" in header or "词曲及编曲作者" in header:
            title = clean_title_cell(cells[1])
            credit_text = cells[2].get_text("\n", strip=True)
            match = re.search(r"[编編]曲[:：]\s*([^\n]+)", credit_text)
            arranger_text = match.group(1).strip() if match else ""
        else:
            title_index = header.index("曲目")
            arranger_index = header.index("编曲") if "编曲" in header else header.index("編曲")
            title = clean_title_cell(cells[title_index])
            arranger_text = cells[arranger_index].get_text("\n", strip=True)

        arrangers = split_arrangers(arranger_text)
        tracks.append(
            {
                "title": title,
                "arrangers": arrangers,
                "is_collaboration": len(arrangers) > 1,
            }
        )

    return {
        "album": album_meta["album"],
        "canonical_title": canonical_title,
        "query_title": album_meta["query_title"],
        "release_date": album_meta["release_date"],
        "release_note": album_meta.get("release_note"),
        "year": album_meta["year"],
        "cover_url": extract_cover_url(soup),
        "source_url": page_url(album_meta["query_title"]),
        "tracks": tracks,
    }


def fallback_note(name: str) -> dict:
    return {
        "signature": "合作型编曲",
        "profile": f"{name} 在周杰伦专辑体系里出现次数较少，但能帮助我们看见某个阶段新增的合作面向。",
        "keywords": ["合作", "阶段性", "补色"],
        "representative": [],
    }


def build_arranger_entries(albums: list[dict]) -> list[dict]:
    all_tracks = []
    for album in albums:
        for track in album["tracks"]:
            all_tracks.append(
                {
                    "album": album["album"],
                    "year": album["year"],
                    "release_date": album["release_date"],
                    "source_url": album["source_url"],
                    **track,
                }
            )

    grouped = defaultdict(list)
    for track in all_tracks:
        for arranger in track["arrangers"]:
            grouped[arranger].append(track)

    arranger_entries = []
    for arranger, entries in grouped.items():
        entries.sort(key=lambda item: (item["year"], item["release_date"], item["title"]))
        album_buckets = []
        counts_by_album = []
        bucket_map = defaultdict(list)
        for item in entries:
            bucket_map[item["album"]].append(item["title"])

        for album in albums:
            songs = bucket_map.get(album["album"], [])
            counts_by_album.append(len(songs))
            if songs:
                album_buckets.append(
                    {
                        "album": album["album"],
                        "year": album["year"],
                        "songs": songs,
                    }
                )

        unique_song_count = len({(item["album"], item["title"]) for item in entries})
        notes = ARRANGER_NOTES.get(arranger, fallback_note(arranger))
        suggested = [song for song in notes["representative"] if any(item["title"] == song for item in entries)]
        if len(suggested) < 6:
            for item in entries:
                if item["title"] not in suggested:
                    suggested.append(item["title"])
                if len(suggested) == 6:
                    break

        arranger_entries.append(
            {
                "name": arranger,
                "song_count": unique_song_count,
                "album_count": len(album_buckets),
                "solo_count": sum(1 for item in entries if not item["is_collaboration"]),
                "co_count": sum(1 for item in entries if item["is_collaboration"]),
                "first_year": min(item["year"] for item in entries),
                "last_year": max(item["year"] for item in entries),
                "signature": notes["signature"],
                "profile": notes["profile"],
                "keywords": notes["keywords"],
                "representative": suggested,
                "counts_by_album": counts_by_album,
                "albums": album_buckets,
            }
        )

    arranger_entries.sort(key=lambda item: (-item["song_count"], item["first_year"], item["name"]))
    return arranger_entries


def build_payload() -> dict:
    album_entries = []
    for meta in ALBUMS:
        print(f"Fetching {meta['album']}...", flush=True)
        album_entries.append(extract_tracks(meta))
    arranger_entries = build_arranger_entries(album_entries)

    total_tracks = sum(len(album["tracks"]) for album in album_entries)
    unique_arrangers = len(arranger_entries)
    counter = Counter()
    for arranger in arranger_entries:
        counter[arranger["name"]] = arranger["song_count"]

    payload = {
        "meta": {
            "title": "周杰伦编曲图谱",
            "scope": "16 张录音室专辑正式曲目",
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_albums": len(album_entries),
            "total_tracks": total_tracks,
            "unique_arrangers": unique_arrangers,
            "latest_album": "太阳之子",
            "latest_album_note": "《太阳之子》已纳入统计。公开资料显示：2026-03-24 先公开 MV 并开启实体预售，2026-03-25 数字专辑正式上线。",
            "method": "同一首歌若为多人联编，会分别计入每位编曲人的名下，方便从“谁参与了哪类作品”这个角度观察周杰伦的编曲合作版图。",
            "disclaimer": "编曲人风格关键词与文字描述，为基于代表作品的归纳总结，不是编曲人官方自述。",
            "top_arrangers": counter.most_common(6),
        },
        "albums": album_entries,
        "arrangers": arranger_entries,
        "sources": [
            {
                "label": album["album"],
                "url": album["source_url"],
            }
            for album in album_entries
        ],
    }
    return to_simplified(payload)


def main() -> None:
    payload = build_payload()
    OUTPUT.write_text(
        "window.JAY_ARRANGER_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT}")
    print(
        f"Albums: {payload['meta']['total_albums']}, "
        f"Tracks: {payload['meta']['total_tracks']}, "
        f"Arrangers: {payload['meta']['unique_arrangers']}"
    )


if __name__ == "__main__":
    main()
