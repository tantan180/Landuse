# -*- coding: utf-8 -*-
import os, glob
import numpy as np
import pandas as pd
import rasterio

# ① 设置你的根目录（就是包含 1990、1995… 这些年份文件夹的目录）
root = r"E:\GEOdata\LUCC\CNLUCC\CNLUCC_clipped"

# ② 输出 CSV 路径
out_csv = os.path.join(root, "CNLUCC_unique_values.csv")

rows = []

# ③ 遍历年份文件夹（名字是纯数字的才算）
years = sorted([d for d in os.listdir(root) if d.isdigit()], key=int)

for y in years:
    folder = os.path.join(root, y)
    if not os.path.isdir(folder):
        continue

    # 优先使用 “{year}.tif”，否则取该文件夹中的第一个 .tif
    cand1 = os.path.join(folder, f"{y}.tif")
    if os.path.exists(cand1):
        tif_path = cand1
    else:
        tifs = sorted(glob.glob(os.path.join(folder, "*.tif")))
        if not tifs:
            print(f"[WARN] {y} 文件夹没有找到 .tif，跳过")
            continue
        tif_path = tifs[0]

    try:
        with rasterio.open(tif_path) as src:
            arr = src.read(1)
            nodata = src.nodata
    except Exception as e:
        print(f"[ERROR] 打不开 {tif_path}: {e}")
        continue

    # 去掉 NoData 与 NaN
    if nodata is not None:
        mask = (arr != nodata) & (~np.isnan(arr))
    else:
        mask = ~np.isnan(arr)

    vals = np.unique(arr[mask])
    # 转成整型列表（如果你的栅格是float型且包含小数，请去掉 astype(int)）
    if np.issubdtype(vals.dtype, np.floating):
        # 若类别是整数编码但被存成 float，可安全转 int
        if np.all(np.isclose(vals, np.round(vals))):
            vals = vals.astype(int)

    rows.append({"year": int(y), "unique_values": "[" + ",".join(map(str, vals.tolist())) + "]"})

# ④ 保存 CSV
df = pd.DataFrame(rows).sort_values("year")
df.to_csv(out_csv, index=False, encoding="utf-8-sig")

print(f"已保存唯一值统计到: {out_csv}")
print(df)#成功
