import os
import re
import zipfile
import base64
import tempfile

# 搜索所有 .goodnotes 文件
gn_files = [f for f in os.listdir('.') if f.endswith('.goodnotes')]

if not gn_files:
    print("❌ 未找到任何 .goodnotes 文件！")
    exit()

print(f"📚 检测到 {len(gn_files)} 个卡组，开始批量处理...\n")

# 卡片刷题单页模板（带返回主页按钮）
PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>{deck_name} - 刷题卡</title>
<style>
  :root {{ --bg: #f2f2f7; --card-bg: #fff; --text: #1c1c1e; --primary: #007aff; --danger: #ff3b30; --success: #34c759; }}
  body {{ margin: 0; padding: 16px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--text); display: flex; flex-direction: column; align-items: center; min-height: 90vh; user-select: none; }}
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
    const deck = [{cards_json}];
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

uuid_pattern = re.compile(rb'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}')

deck_stats = []

for gn in sorted(gn_files):
    deck_name = os.path.splitext(gn)[0]
    out_html_name = f"{deck_name}.html"
    print(f"🔄 正在处理: {deck_name} ...")

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with zipfile.ZipFile(gn, 'r') as z:
                z.extractall(temp_dir)
        except Exception as e:
            print(f"❌ 解压失败 {gn}: {e}")
            continue

        pb_file = os.path.join(temp_dir, "index.events.pb")
        att_dir = os.path.join(temp_dir, "attachments")

        if not os.path.exists(att_dir):
            print(f"⚠️ {gn} 缺少附件，跳过")
            continue

        ordered_images = []
        available_files = {f.upper(): f for f in os.listdir(att_dir)}

        if os.path.exists(pb_file):
            with open(pb_file, "rb") as f:
                content = f.read()
            found_uuids = [u.decode('ascii').upper() for u in uuid_pattern.findall(content)]
            seen = set()
            for uid in found_uuids:
                if uid in available_files and uid not in seen:
                    real_filename = available_files[uid]
                    full_p = os.path.join(att_dir, real_filename)
                    with open(full_p, "rb") as img_f:
                        head = img_f.read(16)
                    if head.startswith(b"\xff\xd8\xff") or head.startswith(b"\x89PNG\r\n\x1a\n"):
                        ordered_images.append(full_p)
                        seen.add(uid)

        # 兜底：如果 pb 没解析全，按修改时间
        if len(ordered_images) < 2:
            files = [os.path.join(att_dir, f) for f in os.listdir(att_dir)]
            files.sort(key=lambda x: os.path.getmtime(x))
            for full_p in files:
                with open(full_p, "rb") as img_f:
                    head = img_f.read(16)
                if head.startswith(b"\xff\xd8\xff") or head.startswith(b"\x89PNG\r\n\x1a\n"):
                    ordered_images.append(full_p)

        pairs = []
        for i in range(0, len(ordered_images) - 1, 2):
            pairs.append((ordered_images[i], ordered_images[i+1]))

        cards_js = []
        for idx, (f_img, b_img) in enumerate(pairs):
            with open(f_img, "rb") as f1, open(b_img, "rb") as f2:
                b64_f = base64.b64encode(f1.read()).decode('utf-8')
                b64_b = base64.b64encode(f2.read()).decode('utf-8')
                cards_js.append(f"{{ id: {idx+1}, front: 'data:image/jpeg;base64,{b64_f}', back: 'data:image/jpeg;base64,{b64_b}' }}")

        full_html = PAGE_TEMPLATE.format(
            deck_name=deck_name,
            cards_json=','.join(cards_js)
        )

        with open(out_html_name, "w", encoding="utf-8") as f:
            f.write(full_html)

        # 分类逻辑：分析化学 vs 无机化学
        is_analytical = ("真题简答" in deck_name) or ("指导简答" in deck_name) or ("分析" in deck_name)
        category = "分析化学" if is_analytical else "无机化学"

        deck_stats.append({
            "title": deck_name,
            "filename": out_html_name,
            "count": len(pairs),
            "category": category
        })
        print(f"   ↳ 已生成 [{category}]: {out_html_name} (共 {len(pairs)} 题)")

# 生成导航总主页 index.html
PORTAL_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>化学题库中心</title>
<style>
  :root { --bg: #f2f2f7; --card: #ffffff; --text: #1c1c1e; --primary: #007aff; }
  body { margin: 0; padding: 24px 16px 40px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--text); max-width: 680px; margin: 0 auto; }
  header { margin-bottom: 24px; text-align: center; }
  h1 { font-size: 26px; font-weight: 700; margin: 0 0 6px; }
  .subtitle { font-size: 13px; color: #8e8e93; }
  .section-title { font-size: 16px; font-weight: 700; color: #6e6e73; text-transform: uppercase; margin: 24px 0 12px 6px; display: flex; align-items: center; gap: 6px; }
  .grid { display: flex; flex-direction: column; gap: 10px; }
  .deck-card { background: var(--card); border-radius: 14px; padding: 16px 18px; text-decoration: none; color: inherit; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 8px rgba(0,0,0,0.04); transition: transform 0.1s, background 0.1s; }
  .deck-card:active { transform: scale(0.99); background: #f8f8fb; }
  .deck-info { display: flex; flex-direction: column; gap: 4px; }
  .deck-name { font-size: 16px; font-weight: 600; color: #1c1c1e; }
  .deck-cnt { font-size: 12px; color: #8e8e93; }
  .arrow { color: #c7c7cc; font-size: 18px; font-weight: 600; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; margin-left: 6px; }
  .tag-ana { background: #e0f2fe; color: #0284c7; }
  .tag-inorg { background: #f3e8ff; color: #7e22ce; }
</style>
</head>
<body>
  <header>
    <h1>🧪 化学刷题库</h1>
    <div class="subtitle">离线无闪退 · 极速翻转背题</div>
  </header>

  <div class="section-title">📊 分析化学 <span class="tag tag-ana">重点冲刺</span></div>
  <div class="grid">
    {analytical_cards}
  </div>

  <div class="section-title">⚗️ 无机化学 <span class="tag tag-inorg">元素与理论</span></div>
  <div class="grid">
    {inorganic_cards}
  </div>
</body>
</html>"""

def make_card_html(d):
    return f"""<a href="{d['filename']}" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">{d['title']}</div>
        <div class="deck-cnt">共 {d['count']} 道题目</div>
      </div>
      <div class="arrow">›</div>
    </a>"""

ana_html = "\n".join([make_card_html(d) for d in deck_stats if d["category"] == "分析化学"])
inorg_html = "\n".join([make_card_html(d) for d in deck_stats if d["category"] == "无机化学"])

portal_html = PORTAL_TEMPLATE.format(
    analytical_cards=ana_html or "<div style='color:#999;font-size:13px;padding:8px;'>无内容</div>",
    inorganic_cards=inorg_html or "<div style='color:#999;font-size:13px;padding:8px;'>无内容</div>"
)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(portal_html)

print("\n🎉 全部处理完毕！总目录已生成：index.html")
print("👉 双击 index.html 即可查看完整的分类刷题导航！")
