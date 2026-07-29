import os
import glob
from collections import defaultdict
from osgeo import gdal
import rasterio
import rasterio.windows as windows
from rasterio.warp import reproject, Resampling

# --- 配置区 ---
input_dir = './data/raw'
output_dir = './data/ready/SLC'
# 新增：指定 Sentinel-2 基准影像的绝对路径
master_s2_path = './data/ready/S2/S2_ROI_mosaic_2025-09-14_2025-09-21.tif' 
os.makedirs(output_dir, exist_ok=True)

def align_s1_to_master(s1_raw_path, master_s2_path, out_aligned_path):
    print(f"  -> 正在将 {os.path.basename(s1_raw_path)} 空间对齐至 S2 空间基准...")
    with rasterio.open(master_s2_path) as master:
        dst_crs = master.crs
        dst_transform = master.transform
        dst_width = master.width
        dst_height = master.height
        
    with rasterio.open(s1_raw_path) as src:
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs, 'transform': dst_transform,
            'width': dst_width, 'height': dst_height, 'compress': 'lzw'
        })
        with rasterio.open(out_aligned_path, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i), destination=rasterio.band(dst, i),
                    src_transform=src.transform, src_crs=src.crs,
                    dst_transform=dst_transform, dst_crs=dst_crs,
                    resampling=Resampling.nearest 
                )
    return out_aligned_path

# 步骤1: 扫描所有 .tiff 文件并按日期精准分组
files = glob.glob(os.path.join(input_dir, '*.tiff'))
groups = defaultdict(list)
for file_path in files:
    filename = os.path.basename(file_path)
    if 'S1_' in filename:
        # 【关键修正】原代码 split('_')[0] 只能取到 'S1'，会导致所有日期的影像混为一组。
        # 现根据命名规范 (S1_024463_IW1_20250914T124515...) 提取第4段的日期前8位。
        try:
            date_str = filename.split('_')[3][:8]  # 取出 20250914
            prefix = f"S1_SLC_{date_str}"
        except IndexError:
            prefix = "S1_SLC_unknown"
        groups[prefix].append(file_path)

# 步骤2: 对于每个分组，先拼接后对齐
for prefix, source_files in groups.items():
    if not source_files:
        continue
    print(f"\n处理分组: {prefix} (包含 {len(source_files)} 个碎片文件)")
    
    # 定义过程文件路径
    merged_vrt_path = os.path.join(output_dir, f"{prefix}_temp.vrt")
    merged_raw_tiff = os.path.join(output_dir, f"{prefix}_temp_merged.tiff")
    final_aligned_tiff = os.path.join(output_dir, f"{prefix}_aligned_S2.tiff")
    
    # 子步骤 2.1: 构建虚拟镶嵌 (VRT)
    # 注意：SLC复数数据通常背景为 0+0j，若设置 srcNodata=255 可能会在实部或虚部引起数学计算异常。
    # 这里建议将其设为 None 或 0。
    vrt_options = gdal.BuildVRTOptions(
        resampleAlg='nearest', 
        addAlpha=False
        # srcNodata=0, VRTNodata=0  # 若复数背景为0，可开启此项
    )
    gdal.BuildVRT(merged_vrt_path, source_files, options=vrt_options)
    print(f"  -> VRT 虚拟镶嵌生成完毕")
    
    # 子步骤 2.2: 转化为完整的原始大图 (Raw Merged)
    gdal.Translate(merged_raw_tiff, merged_vrt_path, format='GTiff')
    print(f"  -> 碎片实体合并完成")
    
    # 子步骤 2.3: 将完整大图对齐并裁剪到 S2 基准
    align_s1_to_master(merged_raw_tiff, master_s2_path, final_aligned_tiff)
    print(f"  -> 完美对齐 S2 完成: {final_aligned_tiff}")
    
    # 子步骤 2.4: 自动清理中间临时文件
    for temp_file in [merged_vrt_path, merged_raw_tiff]:
        try:
            os.remove(temp_file)
        except OSError as e:
            print(f"  -> 警告: 删除临时文件 {temp_file} 时出错: {e}")

print("\n✅ 所有 Sentinel-1 影像拼接与基准对齐流程全部完成！")