import rasterio

input_path = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\zero_template.tif"
output_path = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\zero.tif"

with rasterio.open(input_path) as src:
    data = src.read(1)
    meta = src.meta.copy()
    meta.update({"nodata": None})  # 不要设nodata

    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(data, 1)

print(f"nodata已去除，结果保存到: {output_path}")
