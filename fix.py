import os
import shutil

# 遍历解压出来的所有文件夹和无后缀文件
base_dir = "extracted_cards"
output_dir = "recovered_files"
os.makedirs(output_dir, exist_ok=True)

count = 0
for root, dirs, files in os.walk(base_dir):
    for f in files:
        file_path = os.path.join(root, f)
        
        # 读取前几个字节判断文件真实类型
        try:
            with open(file_path, "rb") as fp:
                head = fp.read(16)
                
            ext = None
            if head.startswith(b"\x89PNG\r\n\x1a\n"):
                ext = ".png"
            elif head.startswith(b"\xff\xd8\xff"):
                ext = ".jpg"
            elif head.startswith(b"%PDF"):
                ext = ".pdf"
                
            if ext:
                new_name = f"card_{count:03d}{ext}"
                shutil.copy(file_path, os.path.join(output_dir, new_name))
                print(f"✅ 找回文件: {f} -> {new_name}")
                count += 1
        except Exception as e:
            pass

print(f"\n🎉 搞定！共成功抢救出 {count} 个图片/PDF 文件，全部存放在 'recovered_files' 文件夹里！")
