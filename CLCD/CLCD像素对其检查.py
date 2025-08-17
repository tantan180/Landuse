import os, glob, math
import rasterio

folder = r"E:\GEOdata\LUCC\CLCD\CLCD_CLIPPED"   # 改成你的CLCD目录
files = sorted(glob.glob(os.path.join(folder, "*.tif")))

# 选第一幅作为参考
with rasterio.open(files[0]) as ref:
    ref_crs = ref.crs
    ref_transform = ref.transform
    ref_w, ref_h = ref.width, ref.height
    px_x, px_y = ref.transform.a, -ref.transform.e  # 像元大小

def px_shift(t, ref_t, px_x, px_y):
    # 计算原点相对位移的“像元数”（四舍五入看是否为 0、0.5、1 等）
    dx = (t.c - ref_t.c) / px_x
    dy = (t.f - ref_t.f) / (-px_y)
    return dx, dy

ok = True
for f in files[1:]:
    with rasterio.open(f) as src:
        issues = []
        if src.crs != ref_crs:
            issues.append("CRS不同")
        if not math.isclose(src.transform.a, ref_transform.a, rel_tol=0, abs_tol=1e-9) or \
           not math.isclose(src.transform.e, ref_transform.e, rel_tol=0, abs_tol=1e-9):
            issues.append("像元大小不同")
        if (src.width, src.height) != (ref_w, ref_h):
            issues.append("行列数不同")
        # 旋转检查
        if not (abs(src.transform.b) < 1e-9 and abs(src.transform.d) < 1e-9):
            issues.append("存在旋转(非北向)")
        # 原点偏移（换算为像元）
        dx, dy = px_shift(src.transform, ref_transform, px_x, px_y)
        if abs(dx) > 1e-6 or abs(dy) > 1e-6:
            issues.append(f"原点偏移≈({dx:.3f},{dy:.3f})像元")

        name = os.path.basename(f)
        if issues:
            ok = False
            print(f"[{name}] 不一致：{'; '.join(issues)}")
        else:
            print(f"[{name}] ✅ 与参考完全一致")

if ok:
    print("✅ 所有年份在格网层面完全匹配。")
else:
    print("⚠️ 上面列出的文件存在错位/不一致，需对齐处理。")#2022、2024与母栅格不一致，需要对齐
