import os
import glob

# 输入文件夹（投影后的文件夹）
input_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\pro"  # 替换为你的投影后文件夹路径
# 输出文件夹
output_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\re"  # 替换为你希望输出的文件夹路径

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# 获取所有的TIF文件
tif_files = glob.glob(os.path.join(input_folder, "*.tif"))

# 目标分辨率为1km，设置x、y方向的分辨率均为1000米
for tif_file in tif_files:
    output_tif = os.path.join(output_folder, os.path.basename(tif_file))

    # 使用 gdalwarp 调整分辨率
    cmd = f'gdalwarp -tr 1000 1000 "{tif_file}" "{output_tif}"'

    # 执行命令
    os.system(cmd)
    print(f"分辨率调整为1km完成: {output_tif}")
