# -*- coding: utf-8 -*-
import os
from glob import glob
import numpy as np
import pandas as pd
import rasterio as rio
from tqdm import tqdm

# ======== 路径与参数（按你前面重分类的目录命名）========
ROOT = r"E:\GEOdata\LUCC\CNLUCC\cjy_albers_30m_reclass"  # 每年一个文件夹
FNAME_PATTERN = "*_cjyAEA30m_reclass.tif"                 # 每年文件名模式
OUT_DIR = r"E:\GEOdata\LUCC\CNLUCC\transition_out"        # 输出目录
os.makedirs(OUT_DIR, exist_ok=True)

# 需要计算的时期对
PAIRS = [(1980, 1990), (1990, 2000), (2000, 2010), (2010, 2020)]

# 重分类后的目标类别清单（按行列顺序）
CLASSES = (10, 20, 30, 41, 42, 43, 50, 60, 70, 80)
K = len(CLASSES)
CLASS_TO_INDEX = {c: i for i, c in enumerate(CLASSES)}

# nodata（重分类时我们写成 255）
NODATA = 255

def find_year_file(year_folder):
    """在年份子目录中找到重分类影像"""
    fs = glob(os.path.join(year_folder, FNAME_PATTERN))
    return fs[0] if fs else None

def pixel_area_from_transform(tr):
    # 假设无旋转：面积 = |a * e|
    return abs(tr.a * tr.e)

def accumulate_block(counts_mat, a, b):
    """把一块数据累加到计数矩阵（bincount 快速）"""
    if a.size == 0:
        return
    # 只统计目标类
    m = np.isin(a, CLASSES) & np.isin(b, CLASSES)
    if not m.any():
        return
    ai = np.vectorize(CLASS_TO_INDEX.get)(a[m])
    bi = np.vectorize(CLASS_TO_INDEX.get)(b[m])
    comb = ai * K + bi
    bc = np.bincount(comb, minlength=K * K)
    counts_mat += bc.reshape(K, K)

def transition_matrix_pair(path_a, path_b, nodata=NODATA):
    """两期：交集掩膜统计 -> (counts, area_km2, px_area_m2, valid_pixels)"""
    with rio.open(path_a) as A, rio.open(path_b) as B:
        # 网格必须完全一致
        assert (A.crs == B.crs and A.transform == B.transform and
                A.width == B.width and A.height == B.height), \
            f"Grids not aligned:\n{path_a}\n{path_b}"

        px_area = pixel_area_from_transform(A.transform)
        counts = np.zeros((K, K), dtype=np.int64)
        valid_pixels = 0

        for _, win in tqdm(list(A.block_windows(1)),
                           desc=f"{os.path.basename(path_a)[:10]}→{os.path.basename(path_b)[:10]}"):
            a = A.read(1, window=win)
            b = B.read(1, window=win)
            # 交集有效像元
            valid = (a != nodata) & (b != nodata)
            if not valid.any():
                continue
            valid_pixels += int(valid.sum())
            a = a[valid]; b = b[valid]
            accumulate_block(counts, a, b)

    area_km2 = counts.astype(float) * px_area / 1e6
    return counts, area_km2, px_area, valid_pixels

def save_matrix_csv(mat, out_csv):
    df = pd.DataFrame(mat, index=CLASSES, columns=CLASSES)
    df.to_csv(out_csv, encoding="utf-8-sig")

def main():
    # 预查每年的文件路径
    year_to_file = {}
    for y in sorted({y for p in PAIRS for y in p}):
        ydir = os.path.join(ROOT, str(y))
        f = find_year_file(ydir)
        if not f:
            raise SystemExit(f"未找到年份 {y} 的重分类影像：{ydir}\\{FNAME_PATTERN}")
        year_to_file[y] = f

    # Excel 汇总
    xlsx_path = os.path.join(OUT_DIR, "transitions_1980_2020.xlsx")
    writer = pd.ExcelWriter(xlsx_path, engine="openpyxl")

    summary_rows = []

    for y0, y1 in PAIRS:
        p0 = year_to_file[y0]; p1 = year_to_file[y1]
        counts, area_km2, px_area, valid_pixels = transition_matrix_pair(p0, p1)

        base = f"{y0}_{y1}_transition"
        csv_counts = os.path.join(OUT_DIR, base + "_counts.csv")
        csv_area   = os.path.join(OUT_DIR, base + "_area_km2.csv")
        save_matrix_csv(counts, csv_counts)
        save_matrix_csv(area_km2, csv_area)

        # 行归一概率（from→to）
        row_sum = counts.sum(axis=1, keepdims=True)
        with np.errstate(divide="ignore", invalid="ignore"):
            prob = np.where(row_sum > 0, counts / row_sum, 0.0)
        csv_prob = os.path.join(OUT_DIR, base + "_rowprob.csv")
        save_matrix_csv(np.round(prob, 6), csv_prob)

        # 写入 Excel 多表
        pd.DataFrame(counts, index=CLASSES, columns=CLASSES).to_excel(
            writer, sheet_name=f"counts_{y0}_{y1}")
        pd.DataFrame(area_km2, index=CLASSES, columns=CLASSES).to_excel(
            writer, sheet_name=f"area_km2_{y0}_{y1}")
        pd.DataFrame(np.round(prob, 6), index=CLASSES, columns=CLASSES).to_excel(
            writer, sheet_name=f"prob_{y0}_{y1}")

        summary_rows.append({
            "pair": f"{y0}->{y1}",
            "pixel_area_m2": px_area,
            "valid_pixels_used": valid_pixels,
            "valid_area_km2": valid_pixels * px_area / 1e6,
            "inputA": p0,
            "inputB": p1
        })

        print(f"[{y0}->{y1}] done | px={px_area:.2f} m² | "
              f"valid pixels={valid_pixels} (~{valid_pixels*px_area/1e6:.2f} km²)")
        print(f"CSV: {os.path.basename(csv_counts)}, {os.path.basename(csv_area)}, {os.path.basename(csv_prob)}")

    # 概览表
    pd.DataFrame(summary_rows).to_excel(writer, sheet_name="summary", index=False)
    writer.close()
    print("\nExcel 汇总：", xlsx_path)

if __name__ == "__main__":
    main()
