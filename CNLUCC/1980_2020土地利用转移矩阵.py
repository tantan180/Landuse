# -*- coding: utf-8 -*-
# 1980 ↔ 2020 两期：交集掩膜的土地利用转移矩阵
import os
import numpy as np
import pandas as pd
import rasterio as rio
from tqdm import tqdm

# ========= 配置：把路径改成你的重分类结果 =========
A_PATH = r"E:\GEOdata\LUCC\CNLUCC\cjy_albers_30m_reclass\1980\1980_cjyAEA30m_reclass.tif"
B_PATH = r"E:\GEOdata\LUCC\CNLUCC\cjy_albers_30m_reclass\2020\2020_cjyAEA30m_reclass.tif"
OUT_DIR = r"E:\GEOdata\LUCC\CNLUCC\transition_out1980_2020"   # 输出目录
os.makedirs(OUT_DIR, exist_ok=True)

# 目标类别（重分类后的值）
CLASSES = (10, 20, 30, 41, 42, 43, 50, 60, 70, 80)
K = len(CLASSES)
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}

NODATA = 255  # 重分类时设置的 nodata

def pixel_area_from_transform(tr):
    # 无旋转时：面积 = |a * e|
    return abs(tr.a * tr.e)

def accumulate_block(counts_mat, a, b):
    """把一块数据累加到计数矩阵（用 bincount 更快）"""
    if a.size == 0:
        return
    m = np.isin(a, CLASSES) & np.isin(b, CLASSES)
    if not m.any():
        return
    ai = np.vectorize(CLASS_TO_IDX.get)(a[m])
    bi = np.vectorize(CLASS_TO_IDX.get)(b[m])
    comb = ai * K + bi
    bc = np.bincount(comb, minlength=K*K)
    counts_mat += bc.reshape(K, K)

def transition_matrix_pair(path_a, path_b, nodata=NODATA):
    """两期：交集掩膜统计 -> (counts, area_km2, px_area_m2, valid_pixels)"""
    with rio.open(path_a) as A, rio.open(path_b) as B:
        # 网格必须完全一致（CRS/transform/尺寸）
        assert (A.crs == B.crs and A.transform == B.transform and
                A.width == B.width and A.height == B.height), \
            "Grids not aligned. 请先保证两期完全同网格。"

        px_area = pixel_area_from_transform(A.transform)
        counts = np.zeros((K, K), dtype=np.int64)
        valid_pixels = 0

        for _, win in tqdm(list(A.block_windows(1)),
                           desc=f"{os.path.basename(path_a)[:10]}→{os.path.basename(path_b)[:10]}"):
            a = A.read(1, window=win)
            b = B.read(1, window=win)

            # 交集有效像元（双方都不是 nodata）
            valid = (a != nodata) & (b != nodata)
            if not valid.any():
                continue

            valid_pixels += int(valid.sum())
            accumulate_block(counts, a[valid], b[valid])

    area_km2 = counts.astype(float) * px_area / 1e6
    return counts, area_km2, px_area, valid_pixels

def save_matrix_csv(mat, out_csv):
    pd.DataFrame(mat, index=CLASSES, columns=CLASSES).to_csv(out_csv, encoding="utf-8-sig")

def main():
    counts, area_km2, px_area, valid_px = transition_matrix_pair(A_PATH, B_PATH)

    base = "1980_2020_transition"
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

    print(f"完成 1980→2020 | 像元面积={px_area:.2f} m² | 交集有效像元={valid_px} (~{valid_px*px_area/1e6:.2f} km²)")
    print("CSV 输出：")
    print(os.path.basename(csv_counts))
    print(os.path.basename(csv_area))
    print(os.path.basename(csv_prob))

if __name__ == "__main__":
    main()
