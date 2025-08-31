import os
from glob import glob
import numpy as np
import rasterio
import pandas as pd

# ========= 配置 =========
IN_DIR = r"E:\GEOdata\LUCC\CNLUCC\CNLUCC_CLCD"   # 输入栅格文件夹
PATTERN = "*.tif"                    # 输入文件格式
OUT_CSV = r"E:\GEOdata\LUCC\CNLUCC\CNLUCC_CLCD\cnlucc_unique_values.csv"  # 输出 CSV 路径

# ========= 主程序 =========
records = []

files = sorted(glob(os.path.join(IN_DIR, PATTERN)))
if not files:
    raise SystemExit("未找到输入栅格，请检查 IN_DIR 和 PATTERN")

for path in files:
    fname = os.path.basename(path)
    with rasterio.open(path) as src:
        band = src.read(1, masked=True)  # masked=True 会自动屏蔽 nodata
        unique_vals = np.unique(band.compressed())  # 去掉 nodata 后的唯一值
        # 转成 Python list
        unique_vals = unique_vals.tolist()

    records.append({
        "filename": fname,
        "unique_values": unique_vals
    })
    print(f"{fname}: {unique_vals}")

# 保存到 CSV（唯一值会写成字符串）
df = pd.DataFrame(records)
df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

print(f"\n统计完成，结果保存到 {OUT_CSV}")
