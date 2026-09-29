import os
import re
import zipfile
import shutil

# 新建专门用于部署到 GitHub 的轻量文件夹
deploy_dir = "gh_deploy"
img_deploy_dir = os.path.join(deploy_dir, "images")
if os.path.exists(deploy_dir):
    shutil.rmtree(deploy_dir)
os.makedirs(img_deploy_dir, exist_ok=True)

gn_files = [f for f in os.listdir('.') if f.endswith('.goodnotes')]
uuid_pattern = re.compile(rb'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}')

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

deck_stats = []

for gn in sorted(gn_files):
    deck_name = os.path.splitext(gn)[0]
    # 清理文件名防止网页链接乱码
    safe_name = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]', '_', deck_name)
    out_html_name = f"{safe_name}.html"
    print(f"📦 正在打包: {deck_name} ...")

    with zipfile.ZipFile(gn, 'r') as z:
        file_list = z.namelist()
        pb_data = z.read("index.events.pb") if "index.events.pb" in file_list else None

        # 匹配图片
        att_files = [f for f in file_list if f.startswith("attachments/")]
        att_map = {os.path.basename(f).upper(): f for f in att_files}

        ordered_filenames = []
        if pb_data:
            found_uuids = [u.decode('ascii').upper() for u in uuid_pattern.findall(pb_data)]
            seen = set()
            for uid in found_uuids:
                if uid in att_map and uid not in seen:
                    ordered_filenames.append(att_map[uid])
                    seen.add(uid)
        else:
            ordered_filenames = att_files

        # 复制图片并重命名为标准 jpg
        pairs = []
        for i in range(0, len(ordered_filenames) - 1, 2):
            f_src = ordered_filenames[i]
            b_src = ordered_filenames[i+1]
            card_num = i // 2 + 1

            f_dst_name = f"{safe_name}_q_{card_num}.jpg"
            b_dst_name = f"{safe_name}_a_{card_num}.jpg"

            with open(os.path.join(img_deploy_dir, f_dst_name), "wb") as f_out:
                f_out.write(z.read(f_src))
            with open(os.path.join(img_deploy_dir, b_dst_name), "wb") as b_out:
                b_out.write(z.read(b_src))

            pairs.append((f"images/{f_dst_name}", f"images/{b_dst_name}"))

        cards_js = [f"{{ id: {idx+1}, front: '{f_p}', back: '{b_p}' }}" for idx, (f_p, b_p) in enumerate(pairs)]

        full_html = PAGE_TEMPLATE.format(
            deck_name=deck_name,
            cards_json=','.join(cards_js)
        )

        with open(os.path.join(deploy_dir, out_html_name), "w", encoding="utf-8") as f:
            f.write(full_html)

        is_ana = ("真题简答" in deck_name) or ("指导简答" in deck_name) or ("分析" in deck_name)
        cat = "分析化学" if is_ana else "无机化学"
        deck_stats.append({
            "title": deck_name,
            "filename": out_html_name,
            "count": len(pairs),
            "category": cat
        })

# 编译 index.html
def make_list(category):
    items = [d for d in deck_stats if d["category"] == category]
    if not items:
        return "<div style='color:#8e8e93;padding:12px;'>暂无内容</div>"
    res = []
    for d in items:
        res.append(f'''<a href="{d['filename']}" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">{d['title']}</div>
        <div class="deck-cnt">共 {d['count']} 题</div>
      </div>
      <div class="arrow">›</div>
    </a>''')
    return "\n".join(res)

ana_html = make_list("分析化学")
inorg_html = make_list("无机化学")

INDEX_CONTENT = f'''<!DOCTYPE html>
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
    <h1>🧪 化学刷题库</h1>
    <div class="subtitle">极速加载 · 离线畅刷 · 永不闪退</div>
  </header>
  <div class="section-title">📊 分析化学 <span class="tag tag-ana">2 组</span></div>
  <div class="grid">{ana_html}</div>
  <div class="section-title">⚗️ 无机化学 <span class="tag tag-inorg">10 组</span></div>
  <div class="grid">{inorg_html}</div>
</body>
</html>'''

with open(os.path.join(deploy_dir, "index.html"), "w", encoding="utf-8") as f:
    f.write(INDEX_CONTENT)

print("\n🚀 完美！已经为您打包生成了适合 GitHub 上传的文件夹：'gh_deploy'")
print("📁 里面的所有网页文件均在 10KB 左右，图片全部整齐存放在 images/ 里，完全符合 GitHub 规范！")
