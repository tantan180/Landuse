
import os, math
from glob import glob
import geopandas as gpd
from shapely.geometry import mapping
import rasterio as rio
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.transform import from_origin

# ========= 目录与参数 =========
BASE_DIR   = r"E:\GEOdata\LUCC\CNLUCC\30m"       # 年份为子文件夹
AOI_PATH   = r"E:\GEOdata\cjy\cjy_region.shp"
YEAR_TPL   = 1980                               # 模板年份
PATTERN_IN = "*.tif"                            # 每个年份文件夹里影像通配
OUT_ROOT   = r"E:\GEOdata\LUCC\CNLUCC\cjy_albers_30m"  # 对齐后的输出根目录
PIX_SIZE   = 30.0
DST_NODATA = 255
OUT_DTYPE  = "uint8"

ALBERS = "+proj=aea +lat_1=32 +lat_2=35 +lat_0=30 +lon_0=95 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"

GTIFF = dict(driver="GTiff", compress="LZW", tiled=True,
             blockxsize=512, blockysize=512, BIGTIFF="IF_SAFER")

# ========= 小工具 =========
def pick_one_raster(year_dir):
    """在年份目录中挑一张影像（若有多张，选像元数最大的那张）。"""
    cands = glob(os.path.join(year_dir, PATTERN_IN))
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    # 选面积最大的
    sizes = []
    for p in cands:
        with rio.open(p) as src:
            sizes.append((src.width * src.height, p))
    sizes.sort(reverse=True)
    return sizes[0][1]

def snap_bounds(bounds, s):
    xmin, ymin, xmax, ymax = bounds
    xmin = math.floor(xmin / s) * s
    ymin = math.floor(ymin / s) * s
    xmax = math.ceil (xmax / s) * s
    ymax = math.ceil (ymax / s) * s
    return xmin, ymin, xmax, ymax

def make_year_out_dir(root, year):
    d = os.path.join(root, str(year))
    os.makedirs(d, exist_ok=True)
    return d

# ========= 主流程 =========
def main():
    # 1) 找到所有年份文件夹
    years = sorted([int(os.path.basename(p)) for p in glob(os.path.join(BASE_DIR, "*")) if os.path.isdir(p) and os.path.basename(p).isdigit()])
    assert YEAR_TPL in years, f"找不到模板年份 {YEAR_TPL} 的文件夹"

    # 2) AOI → Albers
    gdf = gpd.read_file(AOI_PATH)
    assert gdf.crs is not None, "AOI 没有 CRS"
    gdf = gdf.to_crs(ALBERS)
    aoi_geom = gdf.unary_union

    # 3) 构建模板网格（以 AOI + 30m）
    xmin, ymin, xmax, ymax = snap_bounds(aoi_geom.bounds, PIX_SIZE)
    width  = int(round((xmax - xmin) / PIX_SIZE))
    height = int(round((ymax - ymin) / PIX_SIZE))
    transform = from_origin(xmin, ymax, PIX_SIZE, PIX_SIZE)
    dst_crs = rio.crs.CRS.from_string(ALBERS)

    # 4) 用 1980 影像生成模板栅格，并裁剪 AOI
    tpl_dir  = os.path.join(BASE_DIR, str(YEAR_TPL))
    tpl_src  = pick_one_raster(tpl_dir)
    assert tpl_src, f"{tpl_dir} 下没有 {PATTERN_IN}"

    out_tpl_dir = make_year_out_dir(OUT_ROOT, YEAR_TPL)
    TPL_OUT = os.path.join(out_tpl_dir, f"{YEAR_TPL}_cjyAEA30m_snap.tif")

    # 先按照固定 grid 重投影
    with rio.open(tpl_src) as src:
        prof = src.profile.copy()
    prof.update(crs=dst_crs, transform=transform, width=width, height=height,
                dtype=OUT_DTYPE, count=1, nodata=DST_NODATA, **GTIFF)

    with rio.open(tpl_src) as src, rio.open(TPL_OUT, "w", **prof) as dst:
        reproject(
            source=rio.band(src, 1),
            destination=rio.band(dst, 1),
            src_transform=src.transform, src_crs=src.crs,
            dst_transform=transform,  dst_crs=dst_crs,
            resampling=Resampling.nearest,
            src_nodata=src.nodata, dst_nodata=DST_NODATA,
            num_threads=2
        )

    # 再按 AOI 精裁（模板 CRS 下）
    from rasterio.mask import mask
    with rio.open(TPL_OUT) as tmp:
        data, new_transform = mask(tmp, [mapping(aoi_geom)], crop=True, filled=True, nodata=DST_NODATA)
        prof2 = tmp.profile.copy()
        prof2.update(transform=new_transform, width=data.shape[2], height=data.shape[1])
    with rio.open(TPL_OUT, "w", **prof2) as dst:
        dst.write(data)
    print("模板完成：", TPL_OUT)

    # 5) 其它年份全部对齐到模板
    with rio.open(TPL_OUT) as tmpl:
        tmpl_prof = tmpl.profile.copy()
        tmpl_tr   = tmpl.transform
        tmpl_crs  = tmpl.crs

    for y in years:
        src_path = pick_one_raster(os.path.join(BASE_DIR, str(y)))
        if not src_path:
            print(f"跳过 {y}: 无影像")
            continue
        out_dir = make_year_out_dir(OUT_ROOT, y)
        out_path = os.path.join(out_dir, f"{y}_cjyAEA30m_snap.tif")

        if y == YEAR_TPL:
            # 模板年已生成；如需统一命名，这里已经就位
            continue

        with rio.open(src_path) as src, rio.open(out_path, "w", **tmpl_prof) as dst:
            reproject(
                source=rio.band(src, 1),
                destination=rio.band(dst, 1),
                src_transform=src.transform, src_crs=src.crs,
                dst_transform=tmpl_tr,    dst_crs=tmpl_crs,
                resampling=Resampling.nearest,
                src_nodata=src.nodata, dst_nodata=tmpl_prof["nodata"],
                num_threads=2
            )
        print("完成：", out_path)

if __name__ == "__main__":
    main()
