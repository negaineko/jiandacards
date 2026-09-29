import os, json, re, shutil, zipfile

# 1. 明确规范的纯净文件名
target_files = {
    "1.吉大真题简答34（03-19）": "1_吉大真题简答34_03_19.html",
    "1.吉大真题简答34 (03-19)": "1_吉大真题简答34_03_19.html",
    "2.学习指导简答37+7 2": "2_学习指导简答37_7_2.html",
    "1碳族元素30": "1碳族元素30.html",
    "2氮族元素41": "2氮族元素41.html",
    "3氧族元素35": "3氧族元素35.html",
    "4卤素40": "4卤素40.html",
    "5铜锌副族元素32": "5铜锌副族元素32.html",
    "6铬锰元素33": "6铬锰元素33.html",
    "7铁系元素29": "7铁系元素29.html",
    "8配合物47": "8配合物47.html",
    "9结构综合97": "9结构综合97.html",
    "推断合集103": "推断合集103.html"
}

# 2. 读取 order_rules.json
with open("order_rules.json", "r", encoding="utf-8") as f:
    order_rules = json.load(f)

# 吉大真题：切除前12张废图
for k in list(order_rules.keys()):
    if "吉大真题" in k and len(order_rules[k]) > 68:
        order_rules[k] = order_rules[k][12:]

# 氮族元素：对调 #0 和 #1
for k in list(order_rules.keys()):
    if "氮族元素" in k and len(order_rules[k]) >= 2:
        order_rules[k][0], order_rules[k][1] = order_rules[k][1], order_rules[k][0]

# 配合物 5 处补卡
peihe_inserts = {
    49: "见学习指导 p246",
    55: "见例题与习题 p258",
    71: "见例题与习题 p279",
    72: "见例题与习题 p280",
    79: "见例题与习题 p282"
}

out_images_dir = "images"
os.makedirs(out_images_dir, exist_ok=True)

gn_files = [f for f in os.listdir('.') if f.endswith('.goodnotes')]
uuid_pattern = re.compile(rb'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}')

def get_orig_sources(gn_path):
    with zipfile.ZipFile(gn_path, 'r') as z:
        names = z.namelist()
        pb_data = z.read("index.events.pb") if "index.events.pb" in names else None
        att_files = [f for f in names if f.startswith("attachments/")]
        att_map = {os.path.basename(f).upper(): f for f in att_files}
        ordered = []
        if pb_data:
            found_uuids = [u.decode('ascii').upper() for u in uuid_pattern.findall(pb_data)]
            seen = set()
            for uid in found_uuids:
                if uid in att_map and uid not in seen:
                    ordered.append(att_map[uid])
                    seen.add(uid)
        else:
            ordered = att_files
        return ordered

peihe_gn = next((f for f in gn_files if "配合物" in f), None)
peihe_targets = {}
if peihe_gn:
    orig_peihe = get_orig_sources(peihe_gn)
    for orig_idx, text in peihe_inserts.items():
        if orig_idx < len(orig_peihe):
            peihe_targets[orig_peihe[orig_idx]] = text

def make_svg(path, text):
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675" width="100%" height="100%">
  <rect width="1200" height="675" fill="#ffffff"/>
  <rect x="24" y="24" width="1152" height="627" rx="16" fill="none" stroke="#d1d1d6" stroke-width="4"/>
  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="52" font-weight="600" fill="#1c1c1e">{text}</text>
</svg>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)

# 3. 生成各章节页面
deck_counts = {}

for deck_key, src_list in order_rules.items():
    matched_gn = next((f for f in gn_files if os.path.splitext(f)[0] == deck_key), None)
    if not matched_gn:
        norm = deck_key.replace("（", "(").replace("）", ")")
        matched_gn = next((f for f in gn_files if os.path.splitext(f)[0].replace("（", "(").replace("）", ")") == norm), None)

    if not matched_gn:
        continue

    deck_name = os.path.splitext(matched_gn)[0]
    safe_prefix = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]', '_', deck_name)
    html_target = target_files.get(deck_key) or target_files.get(deck_name) or f"{safe_prefix}.html"

    final_img_paths = []

    with zipfile.ZipFile(matched_gn, 'r') as z:
        for idx, src in enumerate(src_list):
            out_name = f"{safe_prefix}_{len(final_img_paths):03d}.jpg"
            out_file = os.path.join(out_images_dir, out_name)
            try:
                with open(out_file, "wb") as f_img:
                    f_img.write(z.read(src))
                final_img_paths.append(f"images/{out_name}")
            except Exception:
                continue

            if "配合物" in deck_name and src in peihe_targets:
                svg_name = f"{safe_prefix}_{len(final_img_paths):03d}.svg"
                svg_file = os.path.join(out_images_dir, svg_name)
                make_svg(svg_file, peihe_targets[src])
                final_img_paths.append(f"images/{svg_name}")

            if "结构综合" in deck_name and idx == 146:
                ans_pic = next((f for f in ["6_32_ans.jpg", "6_32_ans.png"] if os.path.exists(f)), None)
                if ans_pic:
                    ext = os.path.splitext(ans_pic)[1]
                    ans_name = f"{safe_prefix}_{len(final_img_paths):03d}{ext}"
                    ans_path = os.path.join(out_images_dir, ans_name)
                    shutil.copy(ans_pic, ans_path)
                    final_img_paths.append(f"images/{ans_name}")

    cards = []
    for i in range(0, len(final_img_paths) - 1, 2):
        cards.append({
            "id": i // 2 + 1,
            "front": final_img_paths[i],
            "back": final_img_paths[i + 1]
        })

    deck_counts[deck_key] = len(cards)
    cards_json = json.dumps(cards, ensure_ascii=False)

    chapter_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>{deck_name} - 刷题卡</title>
<style>
  :root {{ --bg: #f2f2f7; --card-bg: #fff; --text: #1c1c1e; --primary: #007aff; --danger: #ff3b30; --success: #34c759; }}
  body {{ margin: 0; padding: 16px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); display: flex; flex-direction: column; align-items: center; min-height: 90vh; user-select: none; }}
  .header {{ width: 100%; max-width: 680px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }}
  .nav-back {{ font-size: 14px; color: var(--primary); text-decoration: none; font-weight: 600; padding: 6px 10px; background: #e5e5ea; border-radius: 8px; }}
  .deck-title {{ font-size: 15px; font-weight: 600; color: #3a3a3c; max-width: 45%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .btn-reset {{ padding: 6px 12px; font-size: 13px; background: #e5e5ea; border: none; border-radius: 8px; cursor: pointer; color: #1c1c1e; font-weight: 500; }}
  .card-box {{ width: 100%; max-width: 680px; min-height: 380px; max-height: 62vh; height: 52vh; perspective: 1200px; cursor: pointer; }}
  .card-inner {{ width: 100%; height: 100%; position: relative; transform-style: preserve-3d; transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1); border-radius: 18px; box-shadow: 0 10px 25px rgba(0,0,0,0.07); }}
  .card-inner.flipped {{ transform: rotateY(180deg); }}
  .card-face {{ position: absolute; width: 100%; height: 100%; backface-visibility: hidden; background: var(--card-bg); border-radius: 18px; display: flex; justify-content: center; align-items: center; padding: 14px; box-sizing: border-box; overflow: hidden; }}
  .card-back {{ transform: rotateY(180deg); background: #fafbfc; }}
  .card-face img {{ max-width: 100%; max-height: 100%; object-fit: contain; pointer-events: none; }}
  .badge {{ position: absolute; top: 12px; left: 16px; font-size: 11px; font-weight: 700; color: #aeaeb2; letter-spacing: 0.5px; }}
  .prog-tag {{ position: absolute; top: 12px; right: 16px; font-size: 12px; color: #8e8e93; font-weight: 600; }}
  .controls {{ display: flex; gap: 12px; width: 100%; max-width: 680px; margin-top: 18px; }}
  button.action-btn {{ flex: 1; padding: 15px; border-radius: 12px; border: none; font-size: 16px; font-weight: 600; cursor: pointer; transition: transform 0.1s; }}
  button.action-btn:active {{ transform: scale(0.97); }}
  .btn-flip {{ background: var(--primary); color: #fff; }}
  .btn-again {{ background: #ffebeb; color: var(--danger); }}
  .btn-pass {{ background: #e6f9ed; color: var(--success); }}
</style>
</head>
<body>
  <div class="header">
    <a href="index.html" class="nav-back">‹ 目录</a>
    <div class="deck-title">{deck_name}</div>
    <button class="btn-reset" onclick="resetDeck()">重置本轮</button>
  </div>
  <div class="card-box" onclick="flipCard()">
    <div class="card-inner" id="cardInner">
      <div class="card-face card-front">
        <span class="badge">正面 / 题目</span>
        <span class="prog-tag" id="prog"></span>
        <img id="fImg" src="" alt="题目">
      </div>
      <div class="card-face card-back">
        <span class="badge">背面 / 答案</span>
        <img id="bImg" src="" alt="答案">
      </div>
    </div>
  </div>
  <div class="controls">
    <button class="action-btn btn-flip" onclick="flipCard()">翻转</button>
    <button class="action-btn btn-again" onclick="rate(false)">没记住 (重排)</button>
    <button class="action-btn btn-pass" onclick="rate(true)">记住了 (移出)</button>
  </div>
  <script>
    const deck = {cards_json};
    let queue = [...deck];
    let isFlipped = false;
    function update() {{
      isFlipped = false;
      document.getElementById('cardInner').classList.remove('flipped');
      if (queue.length === 0) {{
        document.getElementById('prog').innerText = '🎉 已背完！';
        document.getElementById('fImg').src = '';
        document.getElementById('bImg').src = '';
        return;
      }}
      document.getElementById('prog').innerText = '剩余 ' + queue.length + ' / ' + deck.length;
      document.getElementById('fImg').src = queue[0].front;
      document.getElementById('bImg').src = queue[0].back;
    }}
    function flipCard() {{
      if (queue.length === 0) return;
      isFlipped = !isFlipped;
      document.getElementById('cardInner').classList.toggle('flipped', isFlipped);
    }}
    function rate(pass) {{
      if (queue.length === 0) return;
      if (pass) {{ queue.shift(); }} else {{ queue.push(queue.shift()); }}
      update();
    }}
    function resetDeck() {{ queue = [...deck]; update(); }}
    update();
  </script>
</body>
</html>"""

    with open(html_target, "w", encoding="utf-8") as f_out:
        f_out.write(chapter_html)

# 4. 生成与文件链接精准吻合的原版 index.html
cnt_ji = deck_counts.get("1.吉大真题简答34（03-19）") or deck_counts.get("1.吉大真题简答34 (03-19)", 34)
cnt_xue = deck_counts.get("2.学习指导简答37+7 2", 54)

original_index = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>化学刷题中心</title>
<style>
  body {{
    margin: 0;
    padding: 24px 16px 50px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f2f2f7;
    color: #1c1c1e;
    max-width: 650px;
    margin: 0 auto;
    -webkit-font-smoothing: antialiased;
  }}
  header {{ margin-bottom: 24px; text-align: center; }}
  h1 {{ font-size: 26px; font-weight: 700; margin: 0 0 6px; }}
  .subtitle {{ font-size: 13px; color: #8e8e93; }}
  .section-title {{ font-size: 15px; font-weight: 700; color: #6e6e73; text-transform: uppercase; margin: 24px 0 10px 4px; display: flex; align-items: center; gap: 6px; }}
  .grid {{ display: flex; flex-direction: column; gap: 10px; }}
  .deck-card {{ background: #ffffff; border-radius: 14px; padding: 16px 18px; text-decoration: none; color: inherit; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.04); transition: transform 0.1s, background 0.1s; }}
  .deck-card:active {{ transform: scale(0.98); background: #f8f8fb; }}
  .deck-name {{ font-size: 16px; font-weight: 600; color: #1c1c1e; }}
  .deck-cnt {{ font-size: 12px; color: #8e8e93; margin-top: 3px; }}
  .arrow {{ color: #c7c7cc; font-size: 20px; font-weight: 600; }}
  .tag {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }}
  .tag-ana {{ background: #e0f2fe; color: #0284c7; }}
  .tag-inorg {{ background: #f3e8ff; color: #7e22ce; }}
</style>
</head>
<body>
  <header>
    <h1>🧪 分析&无机化学刷题卡片</h1>
    <div class="subtitle">我恨goodnotes</div>
  </header>
  <div class="section-title">📊 分析化学 <span class="tag tag-ana">2 组</span></div>
  <div class="grid">
    <a href="1_吉大真题简答34_03_19.html" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">1.吉大真题简答34（03-19）</div>
        <div class="deck-cnt">共 {cnt_ji} 题</div>
      </div>
      <div class="arrow">›</div>
    </a>
    <a href="2_学习指导简答37_7_2.html" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">2.学习指导简答37+7 2</div>
        <div class="deck-cnt">共 {cnt_xue} 题</div>
      </div>
      <div class="arrow">›</div>
    </a>
  </div>
  <div class="section-title">⚗️ 无机化学 <span class="tag tag-inorg">10 组</span></div>
  <div class="grid">
    <a href="1碳族元素30.html" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">1碳族元素30</div>
        <div class="deck-cnt">共 {deck_counts.get("1碳族元素30", 31)} 题</div>
      </div>
      <div class="arrow">›</div>
    </a>
    <a href="2氮族元素41.html" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">2氮族元素41</div>
        <div class="deck-cnt">共 {deck_counts.get("2氮族元素41", 42)} 题</div>
      </div>
      <div class="arrow">›</div>
    </a>
    <a href="3氧族元素35.html" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">3氧族元素35</div>
        <div class="deck-cnt">共 {deck_counts.get("3氧族元素35", 35)} 题</div>
      </div>
      <div class="arrow">›</div>
    </a>
    <a href="4卤素40.html" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">4卤素40</div>
        <div class="deck-cnt">共 {deck_counts.get("4卤素40", 40)} 题</div>
      </div>
      <div class="arrow">›</div>
    </a>
    <a href="5铜锌副族元素32.html" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">5铜锌副族元素32</div>
        <div class="deck-cnt">共 {deck_counts.get("5铜锌副族元素32", 32)} 题</div>
      </div>
      <div class="arrow">›</div>
    </a>
    <a href="6铬锰元素33.html" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">6铬锰元素33</div>
        <div class="deck-cnt">共 {deck_counts.get("6铬锰元素33", 33)} 题</div>
      </div>
      <div class="arrow">›</div>
    </a>
    <a href="7铁系元素29.html" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">7铁系元素29</div>
        <div class="deck-cnt">共 {deck_counts.get("7铁系元素29", 30)} 题</div>
      </div>
      <div class="arrow">›</div>
    </a>
    <a href="8配合物47.html" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">8配合物47</div>
        <div class="deck-cnt">共 {deck_counts.get("8配合物47", 47)} 题</div>
      </div>
      <div class="arrow">›</div>
    </a>
    <a href="9结构综合97.html" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">9结构综合97</div>
        <div class="deck-cnt">共 {deck_counts.get("9结构综合97", 97)} 题</div>
      </div>
      <div class="arrow">›</div>
    </a>
    <a href="推断合集103.html" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">推断合集103</div>
        <div class="deck-cnt">共 {deck_counts.get("推断合集103", 103)} 题</div>
      </div>
      <div class="arrow">›</div>
    </a>
  </div>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f_idx:
    f_idx.write(original_index)

# 5. 清理带空格的遗留旧文件
legacy_files = [
    "1.吉大真题简答34 (03-19) .html",
    "2.学习指导简答37+7 2.html",
    "1_吉大真题简答34_03_19_.html"
]
for lf in legacy_files:
    if os.path.exists(lf):
        os.remove(lf)

print("\n🎉 全部修正完成！")
