# -*- coding: utf-8 -*-
import os, glob, math, subprocess, shutil
import rasterio

# === 配置 ===
root = r"E:\GEOdata\LUCC\CLCD\CLCD_CLIPPED"   # ← 放 CLCD_*.tif 的目录
ref_name = "CLCD_2023_Clipped.tif"  # 参考（母格网）
suffix = "_aligned.tif"              # 输出后缀
force_all = False  # True=不检查，直接对齐全部；False=只对齐不一致的

# === 工具函数 ===
def info(fp):
    with rasterio.open(fp) as ds:
        return {
            "crs": ds.crs,
            "transform": ds.transform,  # a b c / d e f / 0 0 1
            "w": ds.width,
            "h": ds.height,
            "px": (ds.transform.a, -ds.transform.e),
            "ul": (ds.transform.c, ds.transform.f),
            "nodata": ds.nodata,
        }

def px_shift(t, tref, px):
    # 返回原点相对位移（单位：像元）
    dx = (t.c - tref.c) / px[0]
    dy = (t.f - tref.f) / px[1]
    return dx, dy

def same_grid(fp, ref_meta, tol=1e-9):
    m = info(fp)
    issues = []

    if m["crs"] != ref_meta["crs"]:
        issues.append("CRS不同")

    if not math.isclose(m["transform"].a, ref_meta["transform"].a, abs_tol=tol) \
       or not math.isclose(m["transform"].e, ref_meta["transform"].e, abs_tol=tol):
        issues.append("像元大小不同")

    if (m["w"], m["h"]) != (ref_meta["w"], ref_meta["h"]):
        issues.append("行列数不同")

    # 是否有旋转（b/d 非零）
    if abs(m["transform"].b) > tol or abs(m["transform"].d) > tol:
        issues.append("存在旋转")

    dx, dy = px_shift(m["transform"], ref_meta["transform"], ref_meta["px"])
    if abs(dx) > 1e-6 or abs(dy) > 1e-6:
        issues.append(f"原点偏移≈({dx:.3f},{dy:.3f})像元")

    return (len(issues) == 0), issues, m

def build_warp_cmd(src, dst, ref_meta, nodata_src=None, nodata_dst=None):
    # 取母格网范围与尺寸（来自 2023）
    xmin = ref_meta["ul"][0]
    ymax = ref_meta["ul"][1]
    xmax = xmin + ref_meta["w"] * ref_meta["px"][0]
    ymin = ymax - ref_meta["h"] * ref_meta["px"][1]

    cmd = [
        "gdalwarp",
        "-r", "near",
        "-t_srs", str(ref_meta["crs"]),  # 用WKT/PROJ字符串
        "-te", str(xmin), str(ymin), str(xmax), str(ymax),
        "-ts", str(ref_meta["w"]), str(ref_meta["h"]),
        "-multi", "-overwrite"
    ]
    # -tr 非必需（-te + -ts 已强制格网对齐）；若想显式加也可：cmd += ["-tr", str(ref_meta["px"][0]), str(ref_meta["px"][1])]

    if nodata_src is not None:
        cmd += ["-srcnodata", str(nodata_src)]
    if nodata_dst is not None:
        cmd += ["-dstnodata", str(nodata_dst)]

    cmd += [src, dst]
    return cmd

def run(cmd):
    print(" ".join(cmd))
    subprocess.check_call(cmd)

# === 主流程 ===
if __name__ == "__main__":
    gw = shutil.which("gdalwarp")
    if not gw:
        raise RuntimeError("未找到 gdalwarp，请先安装 GDAL 并加入 PATH。")

    ref = os.path.join(root, ref_name)
    if not os.path.exists(ref):
        raise FileNotFoundError(f"参考文件不存在: {ref}")

    ref_meta = info(ref)

    tifs = sorted(glob.glob(os.path.join(root, "*.tif")))
    for src in tifs:
        name = os.path.basename(src)
        if name == ref_name:
            print(f"[{name}] 参考文件，跳过")
            continue

        same, issues, m = same_grid(src, ref_meta)
        if not same:
            print(f"[{name}] 不一致：{'; '.join(issues)}")
        else:
            print(f"[{name}] ✅ 与参考一致")

        if force_all or (not same):
            dst = os.path.join(root, os.path.splitext(name)[0] + suffix)
            # nodata：若源有就带上；目标可沿用同值（或设成 0/255 看你的产品编码）
            nodata_src = m.get("nodata", None)
            nodata_dst = nodata_src
            cmd = build_warp_cmd(src, dst, ref_meta, nodata_src, nodata_dst)
            run(cmd)

    print("完成。建议再跑一次你的检查脚本确认全部 ✅。")#完成，1985-2024CLCD完全自己对齐
