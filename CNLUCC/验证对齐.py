import os
from glob import glob
import csv
import numpy as np
import rasterio as rio

# ======= 配置 =======
IN_ROOT   = r"E:\GEOdata\LUCC\CNLUCC\cjy_albers_30m"   # 你裁剪后的结果根目录
PATTERN   = "*_cjyAEA30m_snap_clip.tif"                   # 各年文件通配符
TPL_PATH  = os.path.join(IN_ROOT, "1980", "1980_cjyAEA30m_snap_clip.tif")
OUT_CSV   = r"E:\GEOdata\LUCC\CNLUCC\grid_match_report.csv"
EPS       = 1e-9     # 数值公差（浮点对比）
EPS_BND   = 1e-6     # 较宽松的 bounds 公差（米）

# ======= 工具 =======
def res_from_transform(tr):
    # 分辨率(像元大小)，假设北向上的仿射（旋转项接近0）
    return abs(tr.a), abs(tr.e)

def tr_equal(t1, t2, eps=EPS):
    attrs = ['a','b','c','d','e','f']
    return all(abs(getattr(t1,k) - getattr(t2,k)) <= eps for k in attrs)

def bnd_equal(ds1, ds2, eps=EPS_BND):
    b1, b2 = ds1.bounds, ds2.bounds
    return (abs(b1.left  - b2.left ) <= eps and
            abs(b1.right - b2.right) <= eps and
            abs(b1.top   - b2.top  ) <= eps and
            abs(b1.bottom- b2.bottom) <= eps)

def bool_to_str(x): return "OK" if x else "FAIL"

# ======= 主逻辑 =======
def main():
    # 找到所有年份文件
    year_dirs = sorted([p for p in glob(os.path.join(IN_ROOT, "*")) if os.path.isdir(p)])
    assert os.path.exists(TPL_PATH), f"模板不存在：{TPL_PATH}"

    with rio.open(TPL_PATH) as tpl:
        tpl_tr   = tpl.transform
        tpl_res  = res_from_transform(tpl_tr)
        tpl_crs  = tpl.crs
        tpl_wh   = (tpl.width, tpl.height)
        tpl_nd   = tpl.nodata
        tpl_mask = tpl.read(1, masked=True).mask  # True=nodata

    rows = []
    for yd in year_dirs:
        year = os.path.basename(yd)
        in_files = glob(os.path.join(yd, PATTERN))
        if not in_files:
            rows.append([year, "MISSING", "", "", "", "", "", "", "", ""])
            continue
        path = in_files[0]
        with rio.open(path) as ds:
            ok_crs  = (ds.crs == tpl_crs)
            ok_tr   = tr_equal(ds.transform, tpl_tr, eps=EPS)
            ok_res  = (np.allclose(res_from_transform(ds.transform), tpl_res, atol=EPS))
            ok_wh   = (ds.width == tpl_wh[0] and ds.height == tpl_wh[1])
            ok_bnd  = bnd_equal(ds, tpl, eps=EPS_BND)
            ok_nd   = (ds.nodata == tpl_nd)

            # 掩膜逐像元一致性（确保 AOI 外一致为 nodata）
            m = ds.read(1, masked=True).mask
            # 如果尺寸或 transform 不一致，掩膜比较没有意义
            if ok_tr and ok_wh:
                mask_equal = np.array_equal(m, tpl_mask)
                mask_diff  = int((m ^ tpl_mask).sum())  # 掩膜不一致像元数
            else:
                mask_equal = False
                mask_diff  = -1

        rows.append([
            year,
            bool_to_str(ok_crs),
            bool_to_str(ok_res),
            bool_to_str(ok_tr),
            bool_to_str(ok_bnd),
            bool_to_str(ok_wh),
            bool_to_str(ok_nd),
            bool_to_str(mask_equal),
            mask_diff,
            path
        ])
        print(f"{year}: CRS={ok_crs}, RES={ok_res}, TR={ok_tr}, BND={ok_bnd}, "
              f"WH={ok_wh}, NODATA={ok_nd}, MASK={mask_equal}, DIFF={mask_diff}")

    # 写CSV报告
    header = ["year","crs","resolution","transform","bounds","width_height",
              "nodata","valid_mask_equal","mask_diff_pixels","path"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print("\n校验完成，报告已保存：", OUT_CSV)
    print("说明：列值为 OK/FAIL；mask_diff_pixels 为掩膜不一致的像元个数（0 表示完全一致）。")

if __name__ == "__main__":
    main()
