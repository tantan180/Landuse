import rasterio
import numpy as np
import glob
import os
import pandas as pd

# 冻土栅格文件夹
raster_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\result1"  # 修改为你实际的路径
raster_files = sorted(glob.glob(os.path.join(raster_folder, "*.tif")))  # 按文件名排序

area_list = []

for raster_path in raster_files:
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        # 计算1的像元数
        frozen_pixel = np.sum(data == 1)
        # 单个像元面积（米）
        pixel_area = abs(src.transform[0] * src.transform[4])  # 一般为 1000*1000=1000000 m²
        # 冻土区总面积（单位：平方千米）
        frozen_area_km2 = frozen_pixel * pixel_area / 1e6
        period = os.path.basename(raster_path).split('.')[0]  # 如"1961_1965_TTOP"
        area_list.append({"period": period, "frozen_area_km2": frozen_area_km2})

# 转DataFrame
df = pd.DataFrame(area_list).sort_values("period")
df = df.reset_index(drop=True)

# 计算面积变化量、变化率
df["area_diff"] = df["frozen_area_km2"].diff().fillna(0)
df["area_diff_rate"] = df["area_diff"] / df["frozen_area_km2"].shift(1) * 100
df["area_diff_rate"] = df["area_diff_rate"].fillna(0)

# 输出
print(df)

# 保存到excel
df.to_excel(os.path.join(raster_folder, "frozen_area_stats.xlsx"), index=False)
