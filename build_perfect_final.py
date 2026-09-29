import zipfile, os, re, json, shutil

# 1. 检查规则文件
if not os.path.exists("order_rules.json"):
    print("❌ 错误：未找到 order_rules.json，请确认文件在 cards 目录下！")
    exit(1)

with open("order_rules.json", "r", encoding="utf-8") as f:
    order_rules = json.load(f)

print("✅ 成功加载已整理的规则文件 order_rules.json！")

# 2. 纯代码生成带文字的矢量卡片 (SVG，无需任何第三方图像库)
def generate_text_card_svg(output_path, text):
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675" width="100%" height="100%">
  <rect width="1200" height="675" fill="#ffffff"/>
  <rect x="20" y="20" width="1160" height="635" rx="16" fill="none" stroke="#d1d1d6" stroke-width="4"/>
  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif" font-size="52" font-weight="600" fill="#1c1c1e">{text}</text>
</svg>"""
    with open(output_path, "w", encoding="utf-8") as f_svg:
        f_svg.write(svg_content)

# 3. 初始化输出目录
out_images_dir = "images"
if os.path.exists(out_images_dir):
    shutil.rmtree(out_images_dir)
os.makedirs(out_images_dir, exist_ok=True)

gn_files = [f for f in os.listdir('.') if f.endswith('.goodnotes')]
uuid_pattern = re.compile(rb'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}')

def get_orig_ordered_sources(gn_path):
    with zipfile.ZipFile(gn_path, 'r') as z:
        file_list = z.namelist()
        pb_data = z.read("index.events.pb") if "index.events.pb" in file_list else None
        att_files = [f for f in file_list if f.startswith("attachments/")]
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

# 预先匹配《配合物》指定原序号对应的附件 UUID
peihe_file = next((f for f in gn_files if "配合物" in f), None)
peihe_targets = {}
if peihe_file:
    orig_peihe = get_orig_ordered_sources(peihe_file)
    insert_specs = [
        (49, "见学习指导 p246"),
        (55, "见例题与习题 p258"),
        (71, "见例题与习题 p279"),
        (72, "见例题与习题 p280"),
        (79, "见例题与习题 p282")
    ]
    for orig_i, text in insert_specs:
        if orig_i < len(orig_peihe):
            peihe_targets[orig_peihe[orig_i]] = text

# 4. 构建全部章节
manifest = []

for deck_key, src_list in order_rules.items():
    matched_gn = next((f for f in gn_files if os.path.splitext(f)[0] == deck_key), None)
    if not matched_gn:
        norm_key = deck_key.replace("（", "(").replace("）", ")")
        matched_gn = next((f for f in gn_files if os.path.splitext(f)[0].replace("（", "(").replace("）", ")") == norm_key), None)

    if not matched_gn:
        print(f"⚠️ 跳过：未找到章节【{deck_key}】对应的 .goodnotes 文件")
        continue

    deck_name = os.path.splitext(matched_gn)[0]
    safe_name = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]', '_', deck_name)
    deck_img_dir = os.path.join(out_images_dir, safe_name)
    os.makedirs(deck_img_dir, exist_ok=True)

    final_images = []

    with zipfile.ZipFile(matched_gn, 'r') as z:
        for idx, src in enumerate(src_list):
            img_filename = f"card_{len(final_images):04d}.jpg"
            img_filepath = os.path.join(deck_img_dir, img_filename)
            try:
                with open(img_filepath, "wb") as f_out:
                    f_out.write(z.read(src))
                final_images.append(f"images/{safe_name}/{img_filename}")
            except Exception as e:
                print(f"   读取附件失败 {src}: {e}")
                continue

            # 配合物章节注入文字卡
            if "配合物" in deck_name and src in peihe_targets:
                text = peihe_targets[src]
                c_filename = f"card_{len(final_images):04d}.svg"
                c_filepath = os.path.join(deck_img_dir, c_filename)
                generate_text_card_svg(c_filepath, text)
                final_images.append(f"images/{safe_name}/{c_filename}")
                print(f"   🌟【配合物】成功在题目后插入文字卡: {text}")

            # 结构综合 6.32 补图（第 146 号题后）
            if "结构综合" in deck_name and idx == 146:
                ans_file = next((f for f in ["6_32_ans.jpg", "6_32_ans.png"] if os.path.exists(f)), None)
                if ans_file:
                    ext = os.path.splitext(ans_file)[1]
                    ans_filename = f"card_{len(final_images):04d}{ext}"
                    ans_filepath = os.path.join(deck_img_dir, ans_filename)
                    shutil.copy(ans_file, ans_filepath)
                    final_images.append(f"images/{safe_name}/{ans_filename}")
                    print(f"   🌟【结构综合】成功在 6.32 题目后插入答案图: {ans_file}")

    # 卡片成对整合
    cards = []
    for i in range(0, len(final_images) - 1, 2):
        cards.append({
            "id": i // 2 + 1,
            "front": final_images[i],
            "back": final_images[i + 1]
        })

    html_filename = f"{safe_name}.html"
    manifest.append({"name": deck_name, "file": html_filename, "count": len(cards)})

    card_html = f"""<!DOCTYPE html>
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
        <img id="cardImg" src="" alt="卡片内容">
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

    with open(html_filename, "w", encoding="utf-8") as f_html:
        f_html.write(card_html)

# 5. 生成主页 index.html
manifest_sorted = sorted(manifest, key=lambda x: x['name'])
links_html = "".join([f'<a class="deck-item" href="{d["file"]}"><div class="deck-name">{d["name"]}</div><div class="deck-count">{d["count"]} 组题卡 ›</div></a>' for d in manifest_sorted])

index_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<title>化学刷题卡背题系统</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: env(safe-area-inset-top) 20px env(safe-area-inset-bottom); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f2f2f7; color: #1c1c1e; }}
  .header {{ padding: 24px 0 16px; font-size: 26px; font-weight: 800; }}
  .deck-list {{ display: flex; flex-direction: column; gap: 12px; }}
  .deck-item {{ display: flex; justify-content: space-between; align-items: center; background: #fff; padding: 18px 20px; border-radius: 14px; text-decoration: none; color: inherit; box-shadow: 0 2px 8px rgba(0,0,0,0.04); font-size: 16px; font-weight: 600; }}
  .deck-item:active {{ background: #e5e5ea; }}
  .deck-count {{ font-size: 14px; color: #8e8e93; font-weight: normal; }}
</style>
</head>
<body>
  <div class="header">📚 无机化学闪卡</div>
  <div class="deck-list">
    {links_html}
  </div>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f_idx:
    f_idx.write(index_html)

print("\n🎉 全部章节构建完成！所有缺页与文字答案卡已自动注入！")
