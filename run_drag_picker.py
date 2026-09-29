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
            items.append({"id": f"{safe_name}_{i}", "orig_idx": i, "img": img_path, "src": src})
        deck_data[deck_name] = items

json_str = json.dumps(deck_data, ensure_ascii=False)

html_template = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>卡片序列可视化整理器 (带序号+拖拽排序)</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f2f2f7; margin: 0; padding: 20px 20px 80px 240px; color: #1c1c1e; }
  .sidebar { position: fixed; top: 0; left: 0; width: 220px; height: 100vh; background: #fff; border-right: 1px solid #d1d1d6; overflow-y: auto; padding: 15px 10px; box-sizing: border-box; }
  .sidebar h3 { font-size: 13px; color: #8e8e93; margin-left: 6px; }
  .sidebar a { display: block; padding: 8px 10px; font-size: 13px; color: #007aff; text-decoration: none; border-radius: 6px; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sidebar a:hover { background: #e5e5ea; }
  .deck-box { background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; margin-top: 15px; }
  .card-item { border: 2px solid #e5e5ea; border-radius: 8px; padding: 10px; background: #fff; cursor: grab; user-select: none; transition: transform 0.1s, box-shadow 0.1s; }
  .card-item:active { cursor: grabbing; }
  .card-item.dragging { opacity: 0.35; border: 2px dashed #007aff; }
  .card-item.deleted { opacity: 0.25; filter: grayscale(100%); border-color: #ff3b30 !important; background: #ffebeb !important; }
  .card-header { display: flex; justify-content: space-between; align-items: center; font-size: 13px; margin-bottom: 8px; }
  .idx-badge { font-size: 18px; font-weight: 800; color: #007aff; }
  .orig-idx { font-size: 11px; color: #8e8e93; margin-left: 4px; }
  .role-tag { font-size: 12px; font-weight: 600; padding: 2px 6px; border-radius: 4px; }
  .tag-front { background: #e0f2fe; color: #0284c7; }
  .tag-back { background: #dcfce7; color: #15803d; }
  .tag-del { background: #fee2e2; color: #dc2626; }
  .del-btn { color: #ff3b30; cursor: pointer; font-size: 12px; padding: 2px 6px; border: 1px solid #ff3b30; border-radius: 4px; margin-left: 6px; }
  .card-item img { width: 100%; height: 160px; object-fit: contain; background: #fafafa; border-radius: 4px; border: 1px solid #eee; pointer-events: none; }
  .bottom-bar { position: fixed; bottom: 0; left: 220px; right: 0; height: 60px; background: #fff; border-top: 1px solid #d1d1d6; display: flex; align-items: center; justify-content: space-between; padding: 0 30px; box-shadow: 0 -2px 10px rgba(0,0,0,0.05); }
  .save-btn { background: #007aff; color: #fff; border: none; padding: 10px 24px; font-size: 15px; font-weight: bold; border-radius: 8px; cursor: pointer; }
  .save-btn:hover { background: #0056b3; }
</style>
</head>
<body>
  <div class="sidebar" id="sidebar"></div>
  <div id="content"></div>
  <div class="bottom-bar">
    <span>💡 <b>操作指南：</b>左上角显示当前序号 <b>#0, #1...</b>。直接<b>拖拽卡片</b>调整顺序，序号与题答标签会自动重排！</span>
    <button class="save-btn" onclick="exportConfig()">导出最终排布 (order_rules.json)</button>
  </div>

<script>
const rawDeckData = """ + json_str + """;
let currentDecks = {};

function init() {
  const sidebar = document.getElementById('sidebar');
  sidebar.innerHTML = '<h3>章节导航</h3>';
  
  for (let name in rawDeckData) {
    currentDecks[name] = rawDeckData[name].map(item => ({...item, deleted: false}));
    const id = encodeURIComponent(name).replace(/%/g, '_');
    sidebar.innerHTML += `<a href="#${id}">${name}</a>`;
  }
  renderAll();
}

function renderAll() {
  const content = document.getElementById('content');
  content.innerHTML = '';

  for (let name in currentDecks) {
    const id = encodeURIComponent(name).replace(/%/g, '_');
    const items = currentDecks[name];
    
    let html = `<div class="deck-box" id="${id}"><h2>${name} (当前共 ${items.length} 张)</h2><div class="grid" id="grid_${id}">`;
    
    let currentIdx = 0;
    items.forEach((item) => {
      let roleText = "已作废 ❌";
      let tagClass = "tag-del";
      let displayIdx = "-";

      if (!item.deleted) {
        displayIdx = "#" + currentIdx;
        if (currentIdx % 2 === 0) {
          roleText = "【正面 题目】";
          tagClass = "tag-front";
        } else {
          roleText = "【背面 答案】";
          tagClass = "tag-back";
        }
        currentIdx++;
      }

      html += `
        <div class="card-item ${item.deleted ? 'deleted' : ''}" 
             draggable="true" 
             id="node_${item.id}" 
             data-id="${item.id}"
             data-deck="${name}">
          <div class="card-header">
            <div>
              <span class="idx-badge">${displayIdx}</span>
              <span class="orig-idx">(原#${item.orig_idx})</span>
            </div>
            <div>
              <span class="role-tag ${tagClass}">${roleText}</span>
              <span class="del-btn" onclick="toggleDel('${name}', '${item.id}')">${item.deleted ? '恢复' : '剔除'}</span>
            </div>
          </div>
          <img src="${item.img}">
        </div>`;
    });
    
    html += '</div></div>';
    content.innerHTML += html;
  }

  attachDragEvents();
}

function toggleDel(deckName, itemId) {
  const list = currentDecks[deckName];
  const target = list.find(x => x.id === itemId);
  if (target) {
    target.deleted = !target.deleted;
    renderAll();
  }
}

function attachDragEvents() {
  const items = document.querySelectorAll('.card-item');
  let draggedEl = null;

  items.forEach(item => {
    item.addEventListener('dragstart', e => {
      draggedEl = item;
      item.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
    });

    item.addEventListener('dragend', () => {
      if (draggedEl) draggedEl.classList.remove('dragging');
      draggedEl = null;
    });

    item.addEventListener('dragover', e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    });

    item.addEventListener('drop', e => {
      e.preventDefault();
      if (!draggedEl || draggedEl === item) return;

      const deckFrom = draggedEl.getAttribute('data-deck');
      const deckTo = item.getAttribute('data-deck');
      if (deckFrom !== deckTo) return;

      const fromId = draggedEl.getAttribute('data-id');
      const toId = item.getAttribute('data-id');

      const list = currentDecks[deckFrom];
      const fromIdx = list.findIndex(x => x.id === fromId);
      const toIdx = list.findIndex(x => x.id === toId);

      const [moved] = list.splice(fromIdx, 1);
      list.splice(toIdx, 0, moved);

      renderAll();
    });
  });
}

function exportConfig() {
  const result = {};
  for (let name in currentDecks) {
    result[name] = currentDecks[name]
      .filter(item => !item.deleted)
      .map(item => item.src);
  }
  const blob = new Blob([JSON.stringify(result, null, 2)], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'order_rules.json';
  a.click();
  alert('排布规则 order_rules.json 已成功下载！');
}

init();
</script>
</body>
</html>"""

with open("drag_picker.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("\n🎉 序号增强版已更新完成！正在重新为您打开...")
os.system("open drag_picker.html")
