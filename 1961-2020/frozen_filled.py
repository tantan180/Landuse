import rasterio
import numpy as np
import os


def con_single_base(frozen_path, base_path, output_path):
    """
    单基础栅格与单期冻土栅格融合：
    冻土 NoData → 取基础栅格值；否则取冻土值
    :param frozen_path: 单期冻土栅格路径（含 NoData）
    :param base_path: 唯一基础栅格路径（覆盖全区）
    :param output_path: 输出融合结果路径
    """
    with rasterio.open(frozen_path) as frozen_ds, \
            rasterio.open(base_path) as base_ds:
        # 检查空间参考、像元大小（不一致则需预处理，这里简化）
        assert frozen_ds.crs == base_ds.crs, "CRS 不匹配！"
        assert np.allclose(frozen_ds.transform, base_ds.transform), "像元大小/变换不匹配！"

        # 读取数据与掩码
        frozen_arr = frozen_ds.read(1)
        frozen_mask = frozen_ds.read_masks(1) == 0  # True 表示 NoData

        base_arr = base_ds.read(1)

        # 核心逻辑：NoData 区域填基础值，否则保留冻土值
        output_arr = np.where(frozen_mask, base_arr, frozen_arr)

        # 写入结果（复用冻土栅格的元数据）
        profile = frozen_ds.profile
        profile.update(dtype=output_arr.dtype, count=1)

        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(output_arr, 1)


# 批量处理配置
frozen_dir = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\TTOP_albers_1km_alignedd"  # 多期冻土栅格文件夹
base_path = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\zero.tif"  # 唯一基础栅格
output_dir = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\result"  # 输出文件夹

os.makedirs(output_dir, exist_ok=True)

# 遍历多期冻土栅格，逐个与基础栅格融合
for frozen_name in os.listdir(frozen_dir):
    if frozen_name.endswith(".tif"):
        frozen_path = os.path.join(frozen_dir, frozen_name)
        output_path = os.path.join(output_dir, f"fused_{frozen_name}")

        con_single_base(frozen_path, base_path, output_path)
        print(f"已处理 {frozen_name} → 输出至 {output_path}")




#成功运行！！Con(IsNull("冻土栅格"), "基础栅格", "冻土栅格")
