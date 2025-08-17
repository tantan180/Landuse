# -*- coding: utf-8 -*-
import os, glob, math, subprocess, shutil
import rasterio

# ======== 配置 ========
REF_TIF = r"E:\GEOdata\LUCC\CLCD\CLCD_CLIPPED\CLCD_2023_Clipped.tif"   # 母格网（30m）
CNLUCC_ROOT = r"E:\GEOdata\LUCC\CNLUCC\30m"                    # CNLUCC 根目录（可递归）
OUT_SUFFIX = "_toCLCD.tif"
FORCE_ALL = True
# =====================
# —— 裁剪边界（必须设置为你的矢量路径）——
CUTLINE = r"E:\GEOdata\长江源\长江源区径流及土壤水分变化（2003-2018）\cjy_region_Buffer.shp"           # 可为 .shp / .geojson / .gpkg
CUTLINE_LAYER = None                              # 若是GeoPackage/多图层，写层名；单层shp/geojson可留空或None
CUTLINE_WHERE = ""                                 # 属性过滤SQL（如: "region='QTP'"); 无则空串
MANUAL_DST_NODATA = None   # 统一目标nodata；默认沿用源
# =======================

def get_meta(fp):
    with rasterio.open(fp) as ds:
        tr = ds.transform
        return {
            "crs": ds.crs,
            "crs_wkt": ds.crs.to_wkt() if ds.crs else None,
            "tr": tr,
            "w": ds.width, "h": ds.height,
            "px": (tr.a, -tr.e),
            "ul": (tr.c, tr.f),
            "nodata": ds.nodata,
        }

def extent_from_ref(ref):
    xmin = ref["ul"][0]
    ymax = ref["ul"][1]
    xmax = xmin + ref["w"] * ref["px"][0]
    ymin = ymax - ref["h"] * ref["px"][1]
    return xmin, ymin, xmax, ymax

def same_grid(meta, ref, tol=1e-9):
    issues = []
    if meta["crs_wkt"] != ref["crs_wkt"]:
        issues.append("CRS不同")
    if not math.isclose(meta["tr"].a, ref["tr"].a, abs_tol=tol) or \
       not math.isclose(meta["tr"].e, ref["tr"].e, abs_tol=tol):
        issues.append("像元大小不同")
    if (meta["w"], meta["h"]) != (ref["w"], ref["h"]):
        issues.append("行列数不同")
    if abs(meta["tr"].b) > tol or abs(meta["tr"].d) > tol:
        issues.append("存在旋转")
    dx = (meta["tr"].c - ref["tr"].c) / ref["px"][0]
    dy = (meta["tr"].f - ref["tr"].f) / ref["px"][1]
    if abs(dx) > 1e-6 or abs(dy) > 1e-6:
        issues.append(f"原点偏移≈({dx:.3f},{dy:.3f})像元")
    return (len(issues) == 0), issues

def build_warp_cmd(src, dst, ref, nodata_src=None, nodata_dst=None):
    xmin, ymin, xmax, ymax = extent_from_ref(ref)
    xres, yres = ref["px"]  # 应为(30,30)

    cmd = [
        "gdalwarp",
        "-r", "near",
        "-t_srs", ref["crs_wkt"],           # 与母栅格完全一致
        "-tr", str(xres), str(yres),        # 明确30m
        "-te", str(xmin), str(ymin), str(xmax), str(ymax),  # 同范围
        "-ts", str(ref["w"]), str(ref["h"]),                # 同行列
        "-multi", "-overwrite",
        "-of", "GTiff",
        "-co", "COMPRESS=LZW",
        "-co", "TILED=YES",
        "-co", "BIGTIFF=IF_SAFER",
        # 可选：保留外部透明度（alpha），便于显示裁剪边界（不需要可注释）
        # "-dstalpha"
    ]
    # —— 裁剪边界（cutline 会被自动重投影到 -t_srs）——
    if CUTLINE:
        cmd += ["-cutline", CUTLINE, "-crop_to_cutline"]
        if CUTLINE_LAYER:
            cmd += ["-cl", CUTLINE_LAYER]
        if CUTLINE_WHERE:
            cmd += ["-cwhere", CUTLINE_WHERE]

    if nodata_src is not None:
        cmd += ["-srcnodata", str(nodata_src)]
    if nodata_dst is not None:
        cmd += ["-dstnodata", str(nodata_dst)]

    cmd += [src, dst]
    return cmd

def main():
    if not os.path.exists(REF_TIF):
        raise FileNotFoundError(f"参考母栅格不存在：{REF_TIF}")
    if not shutil.which("gdalwarp"):
        raise RuntimeError("未找到 gdalwarp，请先安装 GDAL 并加入 PATH。")
    if not CUTLINE or not os.path.exists(CUTLINE):
        raise FileNotFoundError("CUTLINE 未设置或路径不存在，请正确配置裁剪边界。")

    ref = get_meta(REF_TIF)
    print(f"[参考] CRS={ref['crs']}, Pixel={ref['px']}, Size=({ref['w']},{ref['h']})")

    # 递归收集所有 .tif
    all_tifs = []
    for r, _, fs in os.walk(CNLUCC_ROOT):
        for f in fs:
            if f.lower().endswith(".tif"):
                all_tifs.append(os.path.join(r, f))
    all_tifs.sort()

    for src in all_tifs:
        # 防止把母栅格本身也处理了（万一放在同一目录）
        if os.path.abspath(src) == os.path.abspath(REF_TIF):
            continue

        meta = get_meta(src)
        ok, issues = same_grid(meta, ref)
        base, _ = os.path.splitext(src)
        dst = base + OUT_SUFFIX

        if ok and not FORCE_ALL:
            print(f"[OK] {os.path.basename(src)} 已与母格网一致（仍会按cutline裁剪对齐）")
            # 即使一致，也建议输出裁剪版；如不需要，可在此 continue
            # continue

        if not ok:
            print(f"[ALIGN] {os.path.basename(src)} 不一致：{'; '.join(issues)} → 对齐+裁剪…")
        else:
            print(f"[CROP] {os.path.basename(src)} 一致 → 按cutline裁剪输出…")

        nodata_src = meta["nodata"]
        nodata_dst = nodata_src  # 或者设成固定值，如 0/255

        cmd = build_warp_cmd(src, dst, ref, nodata_src, nodata_dst)
        print(" ".join(cmd))
        subprocess.check_call(cmd)

    print("完成。用 gdalinfo 检查输出：Pixel Size= (30.000000,-30.000000)，范围与母栅格一致。")

if __name__ == "__main__":
    main()#成功