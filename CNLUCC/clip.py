import os
from glob import glob
import geopandas as gpd
import rasterio as rio
from rasterio.mask import mask
from shapely.geometry import mapping

IN_ROOT  = r"E:\GEOdata\LUCC\CNLUCC\cjy_albers_30m"      # A 脚本输出（矩形）
OUT_ROOT = r"E:\GEOdata\LUCC\CNLUCC\cjy_albers_30m\30m_out_snap_clip"  # 新输出（按 AOI 裁剪）
AOI_PATH = r"E:\GEOdata\cjy\cjy_region.shp"
DST_NODATA = 255
os.makedirs(OUT_ROOT, exist_ok=True)

# 读 AOI 并投到模板 CRS（读取 1980 文件拿 CRS）
tpl_path = os.path.join(IN_ROOT, "1980", "1980_cjyAEA30m_snap.tif")
with rio.open(tpl_path) as tpl:
    tpl_crs = tpl.crs

aoi = gpd.read_file(AOI_PATH).to_crs(tpl_crs).unary_union

def crop_one(src_path, dst_path):
    with rio.open(src_path) as src:
        data, tr = mask(src, [mapping(aoi)], crop=True, filled=True, nodata=DST_NODATA)
        prof = src.profile.copy()
        prof.update(transform=tr, width=data.shape[2], height=data.shape[1])
    with rio.open(dst_path, "w", **prof) as dst:
        dst.write(data)

for year_dir in sorted([p for p in glob(os.path.join(IN_ROOT, "*")) if os.path.isdir(p)]):
    year = os.path.basename(year_dir)
    os.makedirs(os.path.join(OUT_ROOT, year), exist_ok=True)
    in_file = glob(os.path.join(year_dir, "*_cjyAEA30m_snap.tif"))[0]
    out_file = os.path.join(OUT_ROOT, year, f"{year}_cjyAEA30m_snap_clip.tif")
    crop_one(in_file, out_file)
    print("裁剪完成：", out_file)
