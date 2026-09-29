import zipfile, os, re

gn_files = [f for f in os.listdir('.') if f.endswith('.goodnotes')]
uuid_pattern = re.compile(rb'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}')

os.makedirs("debug_imgs", exist_ok=True)

# 目录与正文结构
toc_links = []
sections_html = []

for gn in sorted(gn_files):
    deck_name = os.path.splitext(gn)[0]
    safe_anchor = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]', '_', deck_name)
    toc_links.append(f"<a href='#{safe_anchor}'>{deck_name}</a>")
    
    sec_html = f"<div id='{safe_anchor}' class='deck-sec'><h2>📁 {deck_name}</h2>"
    
    with zipfile.ZipFile(gn, 'r') as z:
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
            
        sec_html += f"<p style='color:#666;'>共提取到 {len(ordered)} 张图片（预期生成 {len(ordered)//2} 组卡片）</p><div class='grid'>"
        
        for i, src in enumerate(ordered):
            img_name = f"{safe_anchor}_{i}.jpg"
            img_path = os.path.join("debug_imgs", img_name)
            with open(img_path, "wb") as f_img:
                f_img.write(z.read(src))
                
            is_front = (i % 2 == 0)
            role = "【默认：正面 题目】" if is_front else "【默认：背面 答案】"
            badge_class = "front-tag" if is_front else "back-tag"
            
            sec_html += f"""
            <div class='item'>
              <div class='header-info'>
                <span class='idx'>#{i}</span>
                <span class='tag {badge_class}'>{role}</span>
              </div>
              <div class='img-wrap'>
                <img src='{img_path}' loading='lazy'>
              </div>
            </div>"""
            
        sec_html += "</div></div>"
        sections_html.append(sec_html)

HTML_PAGE = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>全套化学卡片排查看板</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; margin: 0; padding: 20px 20px 20px 240px; color: #1c1c1e; }}
  .sidebar {{ position: fixed; top: 0; left: 0; width: 220px; height: 100vh; background: #fff; border-right: 1px solid #e5e5ea; overflow-y: auto; padding: 15px 10px; box-sizing: border-box; }}
  .sidebar h3 {{ font-size: 14px; color: #8e8e93; margin-left: 8px; text-transform: uppercase; }}
  .sidebar a {{ display: block; padding: 8px 10px; font-size: 13px; color: #007aff; text-decoration: none; border-radius: 6px; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .sidebar a:hover {{ background: #f2f2f7; }}
  .deck-sec {{ background: #fff; border-radius: 14px; padding: 20px; margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
  .deck-sec h2 {{ margin-top: 0; font-size: 20px; border-bottom: 2px solid #f2f2f7; padding-bottom: 10px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; margin-top: 15px; }}
  .item {{ background: #fafbfc; border: 1px solid #e1e4e8; border-radius: 8px; padding: 10px; display: flex; flex-direction: column; }}
  .header-info {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
  .idx {{ font-size: 16px; font-weight: 700; color: #333; }}
  .tag {{ font-size: 11px; padding: 3px 6px; border-radius: 4px; font-weight: 600; }}
  .front-tag {{ background: #e0f2fe; color: #0284c7; }}
  .back-tag {{ background: #dcfce7; color: #15803d; }}
  .img-wrap {{ flex: 1; display: flex; align-items: center; justify-content: center; background: #fff; border: 1px solid #eee; min-height: 120px; border-radius: 4px; overflow: hidden; }}
  .img-wrap img {{ max-width: 100%; max-height: 180px; object-fit: contain; }}
</style>
</head>
<body>
  <div class="sidebar">
    <h3>快捷跳转</h3>
    {"".join(toc_links)}
  </div>
  <h1 style="margin-top:0;">📋 全题库序列精准排查总览</h1>
  <p style="color:#666;">左侧是章节目录。正常情况下，蓝色的【正面 题目】后面必须紧跟绿色的【背面 答案】。</p>
  {"".join(sections_html)}
</body>
</html>"""

with open("check_all.html", "w", encoding="utf-8") as f:
    f.write(HTML_PAGE)

print("\n🚀 全科目排查看板生成完毕！正在自动在浏览器打开...")
os.system("open check_all.html")
