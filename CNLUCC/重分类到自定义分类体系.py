# -*- coding: utf-8 -*-
import os
from glob import glob
import numpy as np
import pandas as pd
import rasterio as rio
from tqdm import tqdm

# ===== 路径（按你的截图定制） =====
ROOT      = r"E:\GEOdata\LUCC\CNLUCC\cjy_albers_30m"            # 输入父目录（每年一个文件夹）
PATTERN   = "*_cjyAEA30m_snap_clip.tif"                          # 每年文件名模式
TEMPLATE  = os.path.join(ROOT, "1980", "1980_cjyAEA30m_snap_clip.tif")
OUT_ROOT  = r"E:\GEOdata\LUCC\CNLUCC\cjy_albers_30m_reclass"     # 输出父目录
os.makedirs(OUT_ROOT, exist_ok=True)

# ===== 重分类映射（CNLUCC→目标类） =====
RECLASS_MAP = {
    12:10, 21:20, 23:20,24:20, 22:30, 31:41, 32:42, 33:43,
    41:50, 42:50, 43:50, 44:50, 61:60, 62:60, 63:60, 65:60, 66:60, 67:60,
    51:70, 52:70, 53:70, 46:80, 64:80,
}
TARGET_CLASSES = (10,20,30,41,42,43,50,60,70,80)
DST_NODATA = 255
OUT_DTYPE  = "uint8"
PIX_SIZE_M = 30.0
EPS = 1e-9

def pause_exit(msg=None):
    if msg: print("\n[!] " + msg)
    input("\n按 回车 退出...")
    raise SystemExit

def build_lut(maxval=1000, nodata_val=DST_NODATA):
    lut = np.full(maxval+1, nodata_val, dtype=np.uint16)
    for k,v in RECLASS_MAP.items():
        if 0 <= k <= maxval: lut[k] = v
    return lut
LUT = build_lut()

def list_year_dirs(root):
    return sorted([p for p in glob(os.path.join(root, "*"))
                   if os.path.isdir(p) and os.path.basename(p).isdigit()],
                  key=lambda p: int(os.path.basename(p)))

def find_one_tif(year_dir):
    files = glob(os.path.join(year_dir, PATTERN))
    if not files: return None
    return files[0]

def check_grid_against_template(path, tmpl):
    with rio.open(tmpl) as T, rio.open(path) as S:
        if S.crs != T.crs: return False, "CRS 不一致"
        if S.transform != T.transform: return False, "transform 不一致"
        if S.width != T.width or S.height != T.height: return False, "宽高不一致"
        ax, ey = abs(S.transform.a), abs(S.transform.e)
        if not (abs(ax-PIX_SIZE_M)<EPS and abs(ey-PIX_SIZE_M)<EPS):
            return False, f"像元不是 {PIX_SIZE_M} m"
    return True, "OK"

def reclass_block(a, src_nodata):
    out = np.full(a.shape, DST_NODATA, dtype=np.uint16)
    valid = np.ones(a.shape, bool) if src_nodata is None else (a != src_nodata)
    if valid.any():
        vals = np.clip(a[valid], 0, LUT.size-1)
        out[valid] = LUT[vals]
    return out.astype(np.uint8)

def main():
    if not os.path.exists(TEMPLATE):
        pause_exit(f"找不到模板：{TEMPLATE}")
    with rio.open(TEMPLATE) as T:
        ax, ey = abs(T.transform.a), abs(T.transform.e)
        if not (abs(ax-PIX_SIZE_M)<EPS and abs(ey-PIX_SIZE_M)<EPS):
            pause_exit("模板像元不是 30 m，请先修正模板。")
        print(f"模板OK：{T.width}×{T.height} | {ax:.6f}m × {ey:.6f}m | {T.crs}")

    stats = []
    for ydir in list_year_dirs(ROOT):
        year = os.path.basename(ydir)
        src_path = find_one_tif(ydir)
        if not src_path:
            print(f"[跳过]{year}: 未找到 {PATTERN}")
            continue

        ok, why = check_grid_against_template(src_path, TEMPLATE)
        if not ok:
            pause_exit(f"[错误]{year}: {why}\n文件={src_path}")

        out_dir = os.path.join(OUT_ROOT, year); os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{year}_cjyAEA30m_reclass.tif")
        print(f"[重分类]{year} → {out_path}")

        uniq_src = set(); tgt_counts = {c:0 for c in TARGET_CLASSES}; unmapped = set()

        with rio.open(src_path) as src:
            prof = src.profile.copy()
            prof.update(dtype=OUT_DTYPE, nodata=DST_NODATA,
                        compress="LZW", tiled=True, blockxsize=512, blockysize=512)
            with rio.open(out_path, "w", **prof) as dst:
                for _, win in tqdm(list(src.block_windows(1)), desc=year):
                    a = src.read(1, window=win)
                    uniq_src.update(np.unique(a).tolist())
                    b = reclass_block(a, src.nodata)
                    dst.write(b, 1, window=win)
                    vals, cnts = np.unique(b, return_counts=True)
                    for v,n in zip(vals,cnts):
                        if v in tgt_counts: tgt_counts[int(v)] += int(n)
                    if src.nodata is None: src_valid = np.ones(a.shape,bool)
                    else: src_valid = (a != src.nodata)
                    bad = src_valid & (b == DST_NODATA)
                    if bad.any(): unmapped.update(np.unique(a[bad]).tolist())

        stats.append({
            "year": int(year),
            "input_unique_values": sorted(int(x) for x in uniq_src),
            "unmapped_source_values": sorted(int(x) for x in unmapped if x != DST_NODATA),
            **{f"class_{c}_count": tgt_counts[c] for c in TARGET_CLASSES}
        })

    if stats:
        df = pd.DataFrame(stats).sort_values("year")
        csv_path = os.path.join(OUT_ROOT, "_reclass_stats.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"\n[完成] 输出目录：{OUT_ROOT}\n[统计] {csv_path}")
    else:
        pause_exit("没有任何年份被处理，请检查目录结构与文件名。")

    pause_exit("全部完成。")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        pause_exit(f"异常：{e}")
