import zipfile, os, re, json

gn_files = [f for f in os.listdir('.') if f.endswith('.goodnotes')]
uuid_pattern = re.compile(rb'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}')

os.makedirs("debug_imgs", exist_ok=True)
deck_data = {}

for gn in sorted(gn_files):
    deck_name = os.path.splitext(gn)[0]
    safe_name = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]', '_', deck_name)
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
            
        items = []
        for i, src in enumerate(ordered):
            img_name = "%s_%d.jpg" % (safe_name, i)
            img_path = os.path.join("debug_imgs", img_name)
            with open(img_path, "wb") as f_img:
                f_img.write(z.read(src))
            items.append({"idx": i, "img": img_path, "src": src})
        deck_data[deck_name] = items

json_str = json.dumps(deck_data, ensure_ascii=False)

html_template = """<html>
<head>
<meta charset="utf-8">
<title>卡片序列可视化整理器</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f2f2f7; margin: 0; padding: 20px 20px 80px 240px; color: #1c1c1e; }
  .sidebar { position: fixed; top: 0; left: 0; width: 220px; height: 100vh; background: #fff; border-right: 1px solid #d1d1d6; overflow-y: auto; padding: 15px 10px; box-sizing: border-box; }
  .sidebar h3 { font-size: 13px; color: #8e8e93; margin-left: 6px; }
  .sidebar a { display: block; padding: 8px 10px; font-size: 13px; color: #007aff; text-decoration: none; border-radius: 6px; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sidebar a:hover { background: #e5e5ea; }
  .deck-box { background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; margin-top: 15px; }
  .card-item { border: 2px solid #e5e5ea; border-radius: 8px; padding: 10px; background: #fff; cursor: pointer; user-select: none; transition: all 0.15s; }
  .card-item.deleted { opacity: 0.25; filter: grayscale(100%); border-color: #ff3b30; text-decoration: line-through; background: #ffebeb; }
  .card-header { display: flex; justify-content: space-between; font-weight: bold; font-size: 14px; margin-bottom: 8px; }
  .card-item img { width: 100%; height: 160px; object-fit: contain; background: #fafafa; border-radius: 4px; border: 1px solid #eee; }
  .bottom-bar { position: fixed; bottom: 0; left: 220px; right: 0; height: 60px; background: #fff; border-top: 1px solid #d1d1d6; display: flex; align-items: center; justify-content: space-between; padding: 0 30px; box-shadow: 0 -2px 10px rgba(0,0,0,0.05); }
  .save-btn { background: #34c759; color: #fff; border: none; padding: 10px 24px; font-size: 15px; font-weight: bold; border-radius: 8px; cursor: pointer; }
  .save-btn:hover { background: #28a745; }
</style>
</head>
<body>
  <div class="sidebar" id="sidebar"></div>
  <div id="content"></div>
  <div class="bottom-bar">
    <span>💡 <b>操作方式：</b>直接点击卡片可将其「剔除」（红框变暗）。再次点击可取消剔除。</span>
    <button class="save-btn" onclick="exportConfig()">生成剔除规则 (filter_rules.json)</button>
  </div>

<script>
const deckData = """ + json_str + """;
let deletedMap = {};

function render() {
  const sidebar = document.getElementById('sidebar');
  const content = document.getElementById('content');
  sidebar.innerHTML = '<h3>章节导航</h3>';
  content.innerHTML = '';

  for (let name in deckData) {
    deletedMap[name] = new Set();
    const id = encodeURIComponent(name).replace(/%/g, '_');
    sidebar.innerHTML += `<a href="#${id}">${name}</a>`;

    let html = `<div class="deck-box" id="${id}"><h2>${name} (共 ${deckData[name].length} 张)</h2><div class="grid">`;
    deckData[name].forEach(item => {
      html += `
        <div class="card-item" id="card_${id}_${item.idx}" onclick="toggleCard('${name}', ${item.idx}, '${id}')">
          <div class="card-header">
            <span>#${item.idx}</span>
            <span id="tag_${id}_${item.idx}">有效</span>
          </div>
          <img src="${item.img}" loading="lazy">
        </div>`;
    });
    html += '</div></div>';
    content.innerHTML += html;
  }
}

function toggleCard(deck, idx, id) {
  const el = document.getElementById(`card_${id}_${idx}`);
  const tag = document.getElementById(`tag_${id}_${idx}`);
  if (deletedMap[deck].has(idx)) {
    deletedMap[deck].delete(idx);
    el.classList.remove('deleted');
    tag.innerText = '有效';
    tag.style.color = '#1c1c1e';
  } else {
    deletedMap[deck].add(idx);
    el.classList.add('deleted');
    tag.innerText = '已剔除 ❌';
    tag.style.color = '#ff3b30';
  }
}

function exportConfig() {
  const res = {};
  for (let k in deletedMap) {
    res[k] = Array.from(deletedMap[k]);
  }
  const blob = new Blob([JSON.stringify(res, null, 2)], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'filter_rules.json';
  a.click();
  alert('规则文件 filter_rules.json 已保存！');
}

render();
</script>
</body>
</html>"""

with open("picker.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("\n🎉 更新完成！正在重新打开...")
os.system("open picker.html")
