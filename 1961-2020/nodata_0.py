import rasterio
import numpy as np

input_tif = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\TTOP_albers_1km_alignedd\1961_1965_TTOP.tif"
output_tif = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\result\1961_1965_TTOP0.tif"

with rasterio.open(input_tif) as src:
    data = src.read(1)
    meta = src.meta.copy()
    nodata = src.nodata

    # 把所有NoData变为0
    if nodata is not None:
        data_filled = np.where(data == nodata, 0, data)
    else:
        data_filled = data

    # 确保只有0和1
    data_filled[data_filled != 1] = 0

    # 修改元数据，不再设nodata
    meta.update({'nodata': 0, 'dtype': 'uint8'})

    with rasterio.open(output_tif, 'w', **meta) as dst:
        dst.write(data_filled.astype('uint8'), 1)
print("所有NoData已变为0，输出完成！")