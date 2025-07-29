import os
import glob

input_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\cjy1961_2020"      # 裁剪后tif目录
output_folder = r"E:\GEOdata\pemefrost\QTP_permfrost_change_data_1961_2020\pro"   # 重投影后tif目录

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# proj4字符串
proj4 = '"+proj=aea +lat_1=27 +lat_2=45 +lat_0=35 +lon_0=105 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"'

tif_files = glob.glob(os.path.join(input_folder, "*.tif"))

for tif_file in tif_files:
    output_tif = os.path.join(output_folder, os.path.basename(tif_file))
    cmd = f'gdalwarp -t_srs {proj4} "{tif_file}" "{output_tif}"'
    os.system(cmd)
    print(f"重投影完成: {output_tif}")
    #成功运行
