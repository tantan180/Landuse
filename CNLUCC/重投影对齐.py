# -*- coding: utf-8 -*-
"""
CNLUCC 批量“重投影对齐 + 按矢量裁剪”到 CLCD 母格网（30m），并自检几何完全一致。
- 关键：使用 rasterio.band 流式重投影，避免一次性读入大栅格导致内存爆。
"""

import os
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling, transform_geom
from rasterio.features import geometry_mask
from rasterio.crs import CRS
import fiona

# ============ 配置区域（按需修改） ============

REF_TIF = r"E:\GEOdata\LUCC\CLCD\CLCD_CLIPPED\CLCD_2023_Clipped.tif"               # CLCD 母栅格（30m）
CNLUCC_ROOT = r"E:\GEOdata\LUCC\CNLUCC\30m"                   # CNLUCC 根目录（递归找 .tif）
OUT_SUFFIX = "_toCLCD.tif"                                    # 输出后缀

CUTLINE = r"E:\GEOdata\长江源\长江源区径流及土壤水分变化（2003-2018）\cjy_region_Buffer.shp"
CUTLINE_LAYER = None                                          # .gpkg 多图层才需要写；.shp/.geojson 置 None
CUTLINE_WHERE = ""                                            # 可选：属性过滤（如 "name='YZ_source'"）

DEFAULT_DST_NODATA = 255                                      # 源无 nodata 时给的默认值
GDAL_CACHE_MB = 256                                          # GDAL 缓存（MB），按你机器内存可调
# ===========================================


def read_ref_meta(ref_path: str):
    if not os.path.exists(ref_path):
        raise FileNotFoundError(f"参考母栅格不存在：{ref_path}")
    with rasterio.open(ref_path) as ref:
        meta = {
            "crs": ref.crs,
            "transform": ref.transform,
            "width": ref.width,
            "height": ref.height,
            "dtype": ref.dtypes[0],
        }
    return meta


def load_cutline_geoms(cutline_path: str, target_crs: CRS, layer: str | None = None, where: str = ""):
    if not os.path.exists(cutline_path):
        raise FileNotFoundError(f"裁剪矢量不存在：{cutline_path}")

    geoms = []
    with fiona.open(cutline_path, layer=layer) as src:
        if getattr(src, "crs_wkt", None):
            src_crs = CRS.from_wkt(src.crs_wkt)
        elif src.crs:
            src_crs = CRS.from_user_input(src.crs)
        else:
            raise RuntimeError("裁剪矢量没有坐标参考（CRS），请检查文件。")

        records = src if not where else src.filter(where=where)
        for feat in records:
            g = feat.get("geometry")
            if g is None:
                continue
            g2 = transform_geom(src_crs, target_crs, g, precision=15)
            geoms.append(g2)

    if not geoms:
        raise RuntimeError("裁剪矢量未读到有效的面要素（检查图层名/属性过滤/几何是否为空）。")
    return geoms


def decide_dst_nodata(src_nodata, dst_dtype: str):
    if src_nodata is not None:
        return src_nodata
    if "uint8" in dst_dtype or "int8" in dst_dtype:
        return 255
    if "uint16" in dst_dtype or "int16" in dst_dtype:
        return 65535
    return DEFAULT_DST_NODATA


def align_one(src_path: str, out_path: str, ref_meta: dict, geoms: list | None):
    """
    关键点：
    - 不使用 src.read(1)
    - 用 rasterio.band(src, 1) 作为 reproject 的输入（GDAL 内部分块、不会一次性进内存）
    """
    # 用 GDAL 环境变量控制缓存/线程
    with rasterio.Env(GDAL_CACHEMAX=GDAL_CACHE_MB, NUM_THREADS="ALL_CPUS"):
        with rasterio.open(src_path) as src:
            dst_nodata = decide_dst_nodata(src.nodata, src.dtypes[0])

            profile = src.profile.copy()
            profile.update({
                "driver": "GTiff",
                "crs": ref_meta["crs"],
                "transform": ref_meta["transform"],
                "width": ref_meta["width"],
                "height": ref_meta["height"],
                "count": 1,
                "dtype": src.dtypes[0],
                "nodata": dst_nodata,
                "compress": "LZW",
                "tiled": True,
                "BIGTIFF": "IF_SAFER",
            })

            # 目标数组分配到最终大小（母格网）
            dst_arr = np.full((ref_meta["height"], ref_meta["width"]), dst_nodata, dtype=profile["dtype"])

            # ★★★ 流式重投影（不读整幅到内存）
            reproject(
                source=rasterio.band(src, 1),
                destination=dst_arr,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=ref_meta["transform"],
                dst_crs=ref_meta["crs"],
                resampling=Resampling.nearest,
                dst_nodata=dst_nodata,
                num_threads=0  # 由 NUM_THREADS 控制
            )

            # 矢量裁剪（掩膜，不改变几何）
            if geoms:
                mask = geometry_mask(
                    geoms,
                    transform=ref_meta["transform"],
                    invert=True,
                    out_shape=(ref_meta["height"], ref_meta["width"])
                )
                dst_arr[~mask] = dst_nodata

            # 写出
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with rasterio.open(out_path, "w", **profile) as dst:
                dst.write(dst_arr, 1)


def check_match(fp: str, ref_meta: dict, tol: float = 1e-9):
    with rasterio.open(fp) as ds:
        tr = ds.transform
        issues = []
        if ds.crs.to_wkt() != ref_meta["crs"].to_wkt():
            issues.append("CRS不同")
        if not math.isclose(tr.a, ref_meta["transform"].a, abs_tol=tol) or \
           not math.isclose(tr.e, ref_meta["transform"].e, abs_tol=tol):
            issues.append("像元大小不同")
        if (ds.width, ds.height) != (ref_meta["width"], ref_meta["height"]):
            issues.append("行列数不同")
        if abs(tr.b) > tol or abs(tr.d) > tol:
            issues.append("存在旋转(非北向)")
        dx = (tr.c - ref_meta["transform"].c) / ref_meta["transform"].a
        dy = (tr.f - ref_meta["transform"].f) / (-ref_meta["transform"].e)
        if abs(dx) > 1e-6 or abs(dy) > 1e-6:
            issues.append(f"原点偏移≈({dx:.3f},{dy:.3f})像元")
        ok = (len(issues) == 0)
        return ok, issues


def main():
    ref = read_ref_meta(REF_TIF)
    print(f"[参考] CRS={ref['crs']}, Pixel=({ref['transform'].a}, {abs(ref['transform'].e)}) Size=({ref['width']},{ref['height']})")

    geoms = load_cutline_geoms(CUTLINE, ref["crs"], layer=CUTLINE_LAYER, where=CUTLINE_WHERE)
    print(f"[Cutline] 载入 {len(geoms)} 个面要素（已重投影到母格 CRS）")

    # 递归收集
    src_list = []
    for root, _, files in os.walk(CNLUCC_ROOT):
        for f in files:
            if f.lower().endswith(".tif"):
                src_list.append(os.path.join(root, f))
    src_list.sort()
    if not src_list:
        print("未找到任何 .tif，请检查 CNLUCC_ROOT 路径。")
        return

    bad = 0
    for i, src in enumerate(src_list, 1):
        out = os.path.splitext(src)[0] + OUT_SUFFIX
        rel = os.path.relpath(src, CNLUCC_ROOT)
        print(f"[{i:03d}] 处理 {rel} → {os.path.basename(out)}")
        align_one(src, out, ref, geoms=geoms)
        ok, issues = check_match(out, ref)
        if ok:
            print("      ✅ 完全匹配（与母格网逐像元一致）")
        else:
            bad += 1
            print(f"      ❌ 不一致：{'; '.join(issues)}")

    if bad == 0:
        print("\n✅ 结果：所有输出均与 CLCD 母格网完全匹配。")
    else:
        print(f"\n⚠️ 结果：共有 {bad} 个输出不一致，请检查源数据或裁剪几何。")


if __name__ == "__main__":
    main()
##成功