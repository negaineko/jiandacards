import zipfile, os, re, json, shutil

# 1. 强制纠偏规则
# 吉大真题：前面多余的废图（#0-#11）必须砍掉，从有效第1题开始
# 配合物：插入5张缺失的文字卡片
peihe_inserts = {
    49: "见学习指导 p246",
    55: "见例题与习题 p258",
    71: "见例题与习题 p279",
    72: "见例题与习题 p280",
    79: "见例题与习题 p282"
}

# 2. 读取 order_rules.json
with open("order_rules.json", "r", encoding="utf-8") as f:
    order_rules = json.load(f)

# 吉大真题清洗：前12张是废图，直接切除
for k in list(order_rules.keys()):
    if "吉大真题" in k:
        if len(order_rules[k]) > 68:
            print(f"🧹 正在清洗【{k}】：切除前12张历史废图，保留真正的34道题...")
            order_rules[k] = order_rules[k][12:]

# 3. 准备输出目录
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

# 预先找到配合物章节的原图UUID
peihe_gn = next((f for f in gn_files if "配合物" in f), None)
peihe_targets = {}
if peihe_gn:
    orig_peihe = get_orig_sources(peihe_gn)
    for orig_idx, text in peihe_inserts.items():
        if orig_idx < len(orig_peihe):
            peihe_targets[orig_peihe[orig_idx]] = text

# 生成 SVG 文字卡片
def make_svg(path, text):
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675" width="100%" height="100%">
  <rect width="1200" height="675" fill="#ffffff"/>
  <rect x="24" y="24" width="1152" height="627" rx="16" fill="none" stroke="#d1d1d6" stroke-width="4"/>
  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="52" font-weight="600" fill="#1c1c1e">{text}</text>
</svg>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)

# 映射与固定 HTML 文件名
deck_file_map = {
    "1.吉大真题简答34（03-19）": "1_吉大真题简答34_03_19_.html",
    "1.吉大真题简答34 (03-19)": "1_吉大真题简答34_03_19_.html",
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

deck_counts = {}

for deck_key, src_list in order_rules.items():
    # 模糊匹配 goodnotes 文件
    matched_gn = next((f for f in gn_files if os.path.splitext(f)[0] == deck_key), None)
    if not matched_gn:
        norm = deck_key.replace("（", "(").replace("）", ")")
        matched_gn = next((f for f in gn_files if os.path.splitext(f)[0].replace("（", "(").replace("）", ")") == norm), None)

    if not matched_gn:
        continue

    deck_name = os.path.splitext(matched_gn)[0]
    safe_folder = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]', '_', deck_name)
    folder_path = os.path.join(out_images_dir, safe_folder)
    os.makedirs(folder_path, exist_ok=True)

    final_imgs = []

    with zipfile.ZipFile(matched_gn, 'r') as z:
        for idx, src in enumerate(src_list):
            out_name = f"c_{len(final_imgs):04d}.jpg"
            out_file = os.path.join(folder_path, out_name)
            try:
                with open(out_file, "wb") as f_img:
                    f_img.write(z.read(src))
                final_imgs.append(f"images/{safe_folder}/{out_name}")
            except Exception:
                continue

            # 配合物补文字卡
            if "配合物" in deck_name and src in peihe_targets:
                svg_name = f"c_{len(final_imgs):04d}.svg"
                svg_file = os.path.join(folder_path, svg_name)
                make_svg(svg_file, peihe_targets[src])
                final_imgs.append(f"images/{safe_folder}/{svg_name}")

            # 结构综合 6.32 补图
            if "结构综合" in deck_name and idx == 146:
                ans_pic = next((f for f in ["6_32_ans.jpg", "6_32_ans.png"] if os.path.exists(f)), None)
                if ans_pic:
                    ext = os.path.splitext(ans_pic)[1]
                    ans_name = f"c_{len(final_imgs):04d}{ext}"
                    ans_path = os.path.join(folder_path, ans_name)
                    shutil.copy(ans_pic, ans_path)
                    final_imgs.append(f"images/{safe_folder}/{ans_name}")

    # 配对成卡
    cards = []
    for i in range(0, len(final_imgs) - 1, 2):
        cards.append({
            "id": i // 2 + 1,
            "front": final_imgs[i],
            "back": final_imgs[i + 1]
        })

    target_html = deck_file_map.get(deck_key) or deck_file_map.get(deck_name) or f"{safe_folder}.html"
    deck_counts[deck_key] = len(cards)

    html_page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<title>{deck_name}</title>
<style>
  * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
  body {{ margin: 0; padding: env(safe-area-inset-top) 16px env(safe-area-inset-bottom); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f2f2f7; display: flex; flex-direction: column; height: 100vh; }}
  .header {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 0; font-size: 15px; font-weight: 600; color: #1c1c1e; }}
  .btn-link {{ color: #007aff; text-decoration: none; cursor: pointer; }}
  .card-container {{ flex: 1; position: relative; margin-bottom: 16px; perspective: 1000px; }}
  .card {{ width: 100%; height: 100%; background: #fff; border-radius: 18px; box-shadow: 0 4px 16px rgba(0,0,0,0.06); display: flex; flex-direction: column; overflow: hidden; padding: 16px; cursor: pointer; }}
  .badge {{ align-self: flex-start; font-size: 12px; font-weight: 600; padding: 4px 8px; border-radius: 6px; margin-bottom: 10px; }}
  .front-badge {{ background: #f2f2f7; color: #8e8e93; }}
  .back-badge {{ background: #e8f5e9; color: #2e7d32; }}
  .img-box {{ flex: 1; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
  .img-box img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
  .actions {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 10px; height: 50px; }}
  .btn {{ border: none; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; }}
  .btn-flip {{ background: #007aff; color: #fff; }}
  .btn-fail {{ background: #ffebee; color: #c62828; }}
  .btn-pass {{ background: #e8f5e9; color: #2e7d32; }}
</style>
</head>
<body>
  <div class="header">
    <a href="index.html" class="btn-link">‹ 目录</a>
    <span>{deck_name}</span>
    <span id="counter">剩余 0/0</span>
  </div>
  <div class="card-container" onclick="flipCard()">
    <div class="card">
      <div id="sideTag" class="badge front-badge">正面 / 题目</div>
      <div class="img-box">
        <img id="cardImg" src="" alt="题目">
      </div>
    </div>
  </div>
  <div class="actions">
    <button class="btn btn-flip" onclick="flipCard()">翻转</button>
    <button class="btn btn-fail" onclick="nextCard(false)">没记住 (重排)</button>
    <button class="btn btn-pass" onclick="nextCard(true)">记住了 (移出)</button>
  </div>

<script>
const rawCards = {json.dumps(cards, ensure_ascii=False)};
let queue = [...rawCards];
let currentCard = null;
let isFront = true;

function updateCard() {{
  if (queue.length === 0) {{
    document.getElementById('counter').innerText = '已全部掌握！';
    document.getElementById('cardImg').src = '';
    document.getElementById('sideTag').innerText = '🎉 恭喜完成！';
    return;
  }}
  currentCard = queue[0];
  isFront = true;
  document.getElementById('counter').innerText = '剩余 ' + queue.length + ' / ' + rawCards.length;
  document.getElementById('sideTag').innerText = '正面 / 题目';
  document.getElementById('sideTag').className = 'badge front-badge';
  document.getElementById('cardImg').src = currentCard.front;
}}

function flipCard() {{
  if (!currentCard) return;
  isFront = !isFront;
  document.getElementById('sideTag').innerText = isFront ? '正面 / 题目' : '背面 / 答案';
  document.getElementById('sideTag').className = isFront ? 'badge front-badge' : 'badge back-badge';
  document.getElementById('cardImg').src = isFront ? currentCard.front : currentCard.back;
}}

function nextCard(passed) {{
  if (queue.length === 0) return;
  const card = queue.shift();
  if (!passed) queue.push(card);
  updateCard();
}}

updateCard();
</script>
</body>
</html>"""

    with open(target_html, "w", encoding="utf-8") as f_out:
        f_out.write(html_page)

# 4. 生成原版精美样式的 index.html
cnt_ji = deck_counts.get("1.吉大真题简答34（03-19）") or deck_counts.get("1.吉大真题简答34 (03-19)", 34)
cnt_xue = deck_counts.get("2.学习指导简答37+7 2", 54)

index_html_final = f"""<!DOCTYPE html>
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
    <a href="1_吉大真题简答34_03_19_.html" class="deck-card">
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
    f_idx.write(index_html_final)

print("\n🎉 重构与修复全部完成！主页、文件名与题数已恢复完美状态！")
