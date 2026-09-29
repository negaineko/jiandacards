import os
import re
import base64

base_dir = "extracted_cards"
pb_file = os.path.join(base_dir, "index.events.pb")
att_dir = os.path.join(base_dir, "attachments")

if not os.path.exists(pb_file):
    print("❌ 未找到 index.events.pb 文件！")
    exit()

# 从二进制 protobuf 文件中提取所有符合 UUID 格式的字符串
with open(pb_file, "rb") as f:
    content = f.read()

# 匹配标准 UUID 模式 (比如 8-4-4-4-12 位十六进制)
uuid_pattern = re.compile(rb'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}')
found_uuids = [u.decode('ascii').upper() for u in uuid_pattern.findall(content)]

# 筛选出确实存在于 attachments 文件夹且是有效图片的文件
available_files = {f.upper(): f for f in os.listdir(att_dir)}

ordered_images = []
seen = set()
for uid in found_uuids:
    if uid in available_files and uid not in seen:
        real_filename = available_files[uid]
        full_p = os.path.join(att_dir, real_filename)
        # 校验是否是图片 (JPEG / PNG)
        with open(full_p, "rb") as img_f:
            head = img_f.read(16)
        if head.startswith(b"\xff\xd8\xff") or head.startswith(b"\x89PNG\r\n\x1a\n"):
            ordered_images.append(full_p)
            seen.add(uid)

print(f"📊 按照事件时间线共捕获到 {len(ordered_images)} 张卡片图片！")

if len(ordered_images) % 2 != 0:
    print("⚠️ 注意：图片总数不是偶数，可能包含未配对的独立图。将按顺序尽量配对。")

# 两两配对：Front / Back
pairs = []
for i in range(0, len(ordered_images) - 1, 2):
    pairs.append((ordered_images[i], ordered_images[i+1]))

print(f"✅ 成功组装出 {len(pairs)} 组题目/答案配对！")

# 将图片直接转成 Base64 内嵌，生成独立无依赖的单文件 HTML，永不闪退
cards_js = []
for idx, (f_img, b_img) in enumerate(pairs):
    with open(f_img, "rb") as f1, open(b_img, "rb") as f2:
        b64_f = base64.b64encode(f1.read()).decode('utf-8')
        b64_b = base64.b64encode(f2.read()).decode('utf-8')
        cards_js.append(f"{{ id: {idx+1}, front: 'data:image/jpeg;base64,{b64_f}', back: 'data:image/jpeg;base64,{b64_b}' }}")

html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>碳族元素 30 - 刷题卡</title>
<style>
  :root {{ --bg: #f2f2f7; --card-bg: #fff; --text: #1c1c1e; --primary: #007aff; --danger: #ff3b30; --success: #34c759; }}
  body {{ margin: 0; padding: 16px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--text); display: flex; flex-direction: column; align-items: center; min-height: 90vh; user-select: none; }}
  .header {{ width: 100%; max-width: 650px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; font-weight: 600; color: #8e8e93; }}
  .btn-reset {{ padding: 6px 12px; font-size: 13px; background: #e5e5ea; border: none; border-radius: 8px; cursor: pointer; }}
  .card-box {{ width: 100%; max-width: 650px; min-height: 380px; max-height: 60vh; height: 50vh; perspective: 1200px; cursor: pointer; }}
  .card-inner {{ width: 100%; height: 100%; position: relative; transform-style: preserve-3d; transition: transform 0.35s ease; border-radius: 18px; box-shadow: 0 10px 25px rgba(0,0,0,0.08); }}
  .card-inner.flipped {{ transform: rotateY(180deg); }}
  .card-face {{ position: absolute; width: 100%; height: 100%; backface-visibility: hidden; background: var(--card-bg); border-radius: 18px; display: flex; justify-content: center; align-items: center; padding: 12px; box-sizing: border-box; overflow: hidden; }}
  .card-back {{ transform: rotateY(180deg); background: #fafbfc; }}
  .card-face img {{ max-width: 100%; max-height: 100%; object-fit: contain; pointer-events: none; }}
  .badge {{ position: absolute; top: 12px; left: 16px; font-size: 11px; font-weight: 700; color: #aeaeb2; letter-spacing: 0.5px; }}
  .controls {{ display: flex; gap: 12px; width: 100%; max-width: 650px; margin-top: 20px; }}
  button.action-btn {{ flex: 1; padding: 15px; border-radius: 12px; border: none; font-size: 16px; font-weight: 600; cursor: pointer; transition: transform 0.1s; }}
  button.action-btn:active {{ transform: scale(0.97); }}
  .btn-flip {{ background: var(--primary); color: #fff; }}
  .btn-again {{ background: #ffebeb; color: var(--danger); }}
  .btn-pass {{ background: #e6f9ed; color: var(--success); }}
</style>
</head>
<body>
  <div class="header">
    <div id="prog">正在载入题库...</div>
    <button class="btn-reset" onclick="resetDeck()">重置本轮</button>
  </div>
  <div class="card-box" onclick="flipCard()">
    <div class="card-inner" id="cardInner">
      <div class="card-face card-front">
        <span class="badge">正面 / 题目</span>
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
    const deck = [{ ','.join(cards_js) }];
    let queue = [...deck];
    let isFlipped = false;
    function update() {{
      isFlipped = false;
      document.getElementById('cardInner').classList.remove('flipped');
      if (queue.length === 0) {{
        document.getElementById('prog').innerText = '🎉 本轮全背完！共 ' + deck.length + ' 题';
        document.getElementById('fImg').src = '';
        document.getElementById('bImg').src = '';
        return;
      }}
      document.getElementById('prog').innerText = '剩余: ' + queue.length + ' / 总数: ' + deck.length;
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

with open("my_study_deck.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("\n🚀 大功告成！已经生成独享刷题文件: my_study_deck.html")
print("👉 双击 my_study_deck.html 就能立刻在浏览器刷题，再也不用担心 Goodnotes 闪退了！")
