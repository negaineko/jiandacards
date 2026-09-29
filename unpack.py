import os
import zipfile

# 自动在当前文件夹寻找 .goodnotes 文件
files = [f for f in os.listdir('.') if f.endswith('.goodnotes')]

if not files:
    print("❌ 没找到 .goodnotes 文件！请把文件和此脚本放在同一个文件夹内。")
else:
    target_file = files[0]
    print(f"📦 找到文件: {target_file}，正在解压...")
    
    out_dir = "extracted_cards"
    with zipfile.ZipFile(target_file, "r") as z:
        z.extractall(out_dir)
        
    print(f"🎉 解压成功！所有内容已保存在文件夹: {out_dir}")
