import os

# 获取当前已经成功生成的所有 .html 文件（排除 index.html 本身）
html_files = [f for f in os.listdir('.') if f.endswith('.html') and f != 'index.html' and f != 'my_study_deck.html']

deck_stats = []
for f in html_files:
    title = f.replace('.html', '')
    # 判断分类
    is_ana = ("真题简答" in title) or ("指导简答" in title) or ("分析" in title)
    cat = "分析化学" if is_ana else "无机化学"
    deck_stats.append({
        "title": title,
        "filename": f,
        "category": cat
    })

# 排序
deck_stats.sort(key=lambda x: x["title"])

def make_list(category):
    items = [d for d in deck_stats if d["category"] == category]
    if not items:
        return "<div style='color:#8e8e93;padding:12px;'>暂无内容</div>"
    res = []
    for d in items:
        res.append(f'''<a href="{d['filename']}" class="deck-card">
      <div class="deck-info">
        <div class="deck-name">{d['title']}</div>
      </div>
      <div class="arrow">›</div>
    </a>''')
    return "\n".join(res)

ana_html = make_list("分析化学")
inorg_html = make_list("无机化学")

html_content = f'''<!DOCTYPE html>
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
  header {{
    margin-bottom: 24px;
    text-align: center;
  }}
  h1 {{
    font-size: 26px;
    font-weight: 700;
    margin: 0 0 6px;
  }}
  .subtitle {{
    font-size: 13px;
    color: #8e8e93;
  }}
  .section-title {{
    font-size: 15px;
    font-weight: 700;
    color: #6e6e73;
    text-transform: uppercase;
    margin: 24px 0 10px 4px;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .grid {{
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .deck-card {{
    background: #ffffff;
    border-radius: 14px;
    padding: 16px 18px;
    text-decoration: none;
    color: inherit;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    transition: transform 0.1s, background 0.1s;
  }}
  .deck-card:active {{
    transform: scale(0.98);
    background: #f8f8fb;
  }}
  .deck-name {{
    font-size: 16px;
    font-weight: 600;
    color: #1c1c1e;
  }}
  .arrow {{
    color: #c7c7cc;
    font-size: 20px;
    font-weight: 600;
  }}
  .tag {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
  }}
  .tag-ana {{ background: #e0f2fe; color: #0284c7; }}
  .tag-inorg {{ background: #f3e8ff; color: #7e22ce; }}
</style>
</head>
<body>
  <header>
    <h1>🧪 化学刷题库</h1>
    <div class="subtitle">离线无闪退 · 随时随地背题</div>
  </header>

  <div class="section-title">📊 分析化学 <span class="tag tag-ana">2 组</span></div>
  <div class="grid">
    {ana_html}
  </div>

  <div class="section-title">⚗️ 无机化学 <span class="tag tag-inorg">10 组</span></div>
  <div class="grid">
    {inorg_html}
  </div>
</body>
</html>'''

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("🎉 搞定！index.html 已成功生成，包含分析化学与无机化学全部卡组！")
