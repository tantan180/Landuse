# -*- coding: utf-8 -*-
"""
检查：CNLUCC 对齐结果 与 CLCD 母格网 是否逐像元完全匹配
- 投影：完全一致（WKT）
- 像元大小：一致（30m）
- 行列数：一致
- 旋转：无（b=d≈0）
- 原点：无像元级偏移（dx,dy≈0）
"""

import os, math, glob
import rasterio

# ===== 配置 =====
CLCD_REF = r"E:\GEOdata\LUCC\CLCD\CLCD_CLIPPED\CLCD_2023_Clipped.tif"          # CLCD 母栅格（基准）
CNLUCC_DIR = r"E:\GEOdata\LUCC\CNLUCC\30m"                         # CNLUCC 对齐后所在目录（递归查找）
FILENAME_SUFFIX = "_toCLCD.tif"                             # 你的对齐输出后缀（如 1980_toCLCD.tif）
TOL = 1e-9                                                  # 浮点容差
# =================


def meta(fp):
    with rasterio.open(fp) as ds:
        tr = ds.transform
        return {
            "path": fp,
            "crs_wkt": ds.crs.to_wkt() if ds.crs else None,
            "w": ds.width, "h": ds.height,
            "tr": tr,                      # a b c / d e f / 0 0 1
            "px": (tr.a, -tr.e),           # (xres, yres)
            "ul": (tr.c, tr.f),            # (ulx, uly)
        }

def px_shift(tr, tr_ref, xres, yres):
    dx = (tr.c - tr_ref.c) / xres
    dy = (tr.f - tr_ref.f) / yres
    return dx, dy

def check_one(fp, refm):
    m = meta(fp)
    issues = []

    # 1) CRS
    if m["crs_wkt"] != refm["crs_wkt"]:
        issues.append("CRS不同")

    # 2) pixel size
    if not math.isclose(m["tr"].a, refm["tr"].a, abs_tol=TOL) or \
       not math.isclose(m["tr"].e, refm["tr"].e, abs_tol=TOL):
        issues.append("像元大小不同")

    # 3) width/height
    if (m["w"], m["h"]) != (refm["w"], refm["h"]):
        issues.append("行列数不同")

    # 4) rotation
    if abs(m["tr"].b) > TOL or abs(m["tr"].d) > TOL:
        issues.append("存在旋转(非北向)")

    # 5) origin shift in pixels
    dx, dy = px_shift(m["tr"], refm["tr"], refm["px"][0], refm["px"][1])
    if abs(dx) > 1e-6 or abs(dy) > 1e-6:
        issues.append(f"原点偏移≈({dx:.3f},{dy:.3f})像元")

    ok = (len(issues) == 0)
    return ok, issues, (dx, dy), m

def main():
    if not os.path.exists(CLCD_REF):
        raise FileNotFoundError(f"找不到 CLCD 参考栅格：{CLCD_REF}")

    refm = meta(CLCD_REF)
    print(f"[参考] CRS=Albers(与WKT一致性比较) Pixel={refm['px']} Size=({refm['w']},{refm['h']})")

    # 递归收集 CNLUCC 对齐后 tifs
    tifs = []
    for r, _, fs in os.walk(CNLUCC_DIR):
        for f in fs:
            if f.lower().endswith(".tif"):
                # 只检查对齐后的结果；如果你想全查，去掉这个判断
                if FILENAME_SUFFIX and not f.endswith(FILENAME_SUFFIX):
                    continue
                tifs.append(os.path.join(r, f))
    tifs.sort()

    if not tifs:
        print("未找到任何待检栅格，请确认目录与后缀设置。")
        return

    bad = 0
    for i, fp in enumerate(tifs, 1):
        ok, issues, (dx, dy), _ = check_one(fp, refm)
        name = os.path.relpath(fp, CNLUCC_DIR)
        if ok:
            print(f"[{i:03d}] ✅ {name} 与参考完全一致")
        else:
            bad += 1
            print(f"[{i:03d}] ❌ {name} 不一致：{'; '.join(issues)}")

    if bad == 0:
        print("\n✅ 结果：所有 CNLUCC 对齐后栅格与 CLCD 母格网完全匹配。")
    else:
        print(f"\n⚠️ 结果：共有 {bad} 个文件与母格网不一致，请按提示问题修复后再检。")

if __name__ == "__main__":
    main()
#成功实现CNLUCC与CLCD像素匹配