import rasterio
import rasterio.windows as windows
from rasterio.warp import reproject, Resampling
import numpy as np
import joblib
import geopandas as gpd
import rasterstats as rs
from scipy.ndimage import uniform_filter
import os
from contextlib import ExitStack
import warnings
warnings.filterwarnings('ignore')

# --- 配置区 ---
S2_PATH = './data/ready/S2/S2_ROI_mosaic_2025-09-21_2025-10-05.tif'
S1_T1_RAW_PATH = './data/ready/SLC/S1_024463_IW1_20250914T124515_VV_0C08-BURST.tiff'  
S1_T2_RAW_PATH = './data/ready/SLC/S1_024463_IW1_20250926T124515_VV_8AA7-BURST.tiff'
CLF_PATH = './models/tillage_classifier.pkl'
CSB_FIELDS_GPKG = './data/utils/CSB_NE.gpkg'

# 输出文件路径
OUTPUT_FUSED_TIF = './out/Fused_Tillage_Result_0921_1005.tif'
OUTPUT_CONF_TIF = './out/RF_Confidence_0921_1005.tif'
OUTPUT_COH_TIF = './out/S1_Coherence_0921_1005.tif'
OUTPUT_CLOUD_TIF = './out/Cloud_Mask_0921_1005.tif'  # 新增：云掩膜输出路径

# --- 全局控制变量 ---
SAVE_COHERENCE = True
SAVE_CLOUD_MASK = True       # 新增：是否将云掩膜保存为独立 TIFF

CONFIDENCE_THRESHOLD = 0.65  
COHERENCE_THRESHOLD = 0.25   
COH_WINDOW_SIZE = 9     
# --------------------

def align_s1_to_master(s1_raw_path, master_s2_path, out_aligned_path):
    print(f"正在将 {os.path.basename(s1_raw_path)} 空间对齐至 S2 空间基准...")
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

def calc_coherence_block(c1, c2, win_size):
    cross = c1 * np.conj(c2)
    p1 = np.abs(c1)**2
    p2 = np.abs(c2)**2
    
    cross_real_mean = uniform_filter(cross.real, size=win_size, mode='reflect')
    cross_imag_mean = uniform_filter(cross.imag, size=win_size, mode='reflect')
    cross_mean = cross_real_mean + 1j * cross_imag_mean
    
    p1_mean = uniform_filter(p1, size=win_size, mode='reflect')
    p2_mean = uniform_filter(p2, size=win_size, mode='reflect')
    
    return np.abs(cross_mean) / np.sqrt(p1_mean * p2_mean + 1e-10)

def process_and_fuse(s1_t1_aligned, s1_t2_aligned):
    print("加载随机森林分类器...")
    clf = joblib.load(CLF_PATH)
    
    # 提取基准 Profile
    with rasterio.open(S2_PATH) as temp_src:
        profile_uint8 = temp_src.profile.copy()
        profile_uint8.update(dtype=rasterio.uint8, count=1, nodata=255, compress='lzw')
        
        profile_float32 = temp_src.profile.copy()
        profile_float32.update(dtype=rasterio.float32, count=1, nodata=np.nan, compress='lzw')
        
        height, width = temp_src.height, temp_src.width
        block_size = 1024

    with ExitStack() as stack:
        # 1. 打开读取流
        src_s2 = stack.enter_context(rasterio.open(S2_PATH))
        src_s1_t1 = stack.enter_context(rasterio.open(s1_t1_aligned))
        src_s1_t2 = stack.enter_context(rasterio.open(s1_t2_aligned))
        
        # 2. 打开必需的写入流
        dst_class = stack.enter_context(rasterio.open(OUTPUT_FUSED_TIF, 'w', **profile_uint8))
        dst_conf = stack.enter_context(rasterio.open(OUTPUT_CONF_TIF, 'w', **profile_uint8))
        dst_class.set_band_description(1, 'Fused_Tillage_Class')
        dst_conf.set_band_description(1, 'S2_RF_Confidence_0_100')
        
        # 3. 动态打开 Coherence 的写入流
        if SAVE_COHERENCE:
            dst_coh = stack.enter_context(rasterio.open(OUTPUT_COH_TIF, 'w', **profile_float32))
            dst_coh.set_band_description(1, 'Interferometric_Coherence')
            print(f"已启用相干性图像导出: {OUTPUT_COH_TIF}")
            
        # 4. 动态打开 Cloud Mask 的写入流
        if SAVE_CLOUD_MASK:
            dst_cloud = stack.enter_context(rasterio.open(OUTPUT_CLOUD_TIF, 'w', **profile_uint8))
            dst_cloud.set_band_description(1, 'S2_Cloud_Mask')
            print(f"已启用云掩膜图像导出: {OUTPUT_CLOUD_TIF}")
            
        print("执行核心逻辑：动态光谱推理、相干性提取与多源融合...")
        
        for row in range(0, height, block_size):
            for col in range(0, width, block_size):
                win_height = min(block_size, height - row)
                win_width = min(block_size, width - col)
                window = windows.Window(col, row, win_width, win_height)
                
                # 光学推理
                s2_data = src_s2.read(window=window)
                if s2_data.size == 0: continue
                b2, b3, b4 = s2_data[0].astype(np.float32), s2_data[1].astype(np.float32), s2_data[2].astype(np.float32)
                b8, b11, b12 = s2_data[3].astype(np.float32), s2_data[4].astype(np.float32), s2_data[5].astype(np.float32)
                scl = s2_data[6].astype(np.uint8)
                
                eps = 1e-10
                ndvi = (b8 - b4) / (b8 + b4 + eps)
                ndsi = (b3 - b11) / (b3 + b11 + eps)
                bsi = ((b11 + b4) - (b8 + b2)) / ((b11 + b4) + (b8 + b2) + eps)
                ndbsi = (bsi - ndvi) / (bsi + ndvi + eps)
                ndti = (b11 - b12) / (b11 + b12 + eps)
                
                features = np.stack([b2, b3, b4, b8, b11, b12, ndvi, ndsi, bsi, ndbsi, ndti], axis=0)
                feat_flat = features.reshape((11, -1)).T
                feat_flat[np.isnan(feat_flat)] = 0
                
                probas = clf.predict_proba(feat_flat)
                s2_preds = np.argmax(probas, axis=1).reshape((win_height, win_width))
                s2_conf = (np.max(probas, axis=1).reshape((win_height, win_width)) * 100).astype(np.uint8)
                
                # 雷达相干性
                c1 = src_s1_t1.read(1, window=window).astype(np.complex64)
                c2 = src_s1_t2.read(1, window=window).astype(np.complex64)
                s1_coh = calc_coherence_block(c1, c2, COH_WINDOW_SIZE)
                s1_preds = (s1_coh < COHERENCE_THRESHOLD).astype(np.uint8)
                
                # 提取云掩膜布尔矩阵
                cloud_mask = np.isin(scl, [8, 9, 10])
                low_conf_mask = s2_conf < (CONFIDENCE_THRESHOLD * 100)
                
                # 动态融合策略
                final_preds = s2_preds.copy().astype(np.uint8)
                final_preds[cloud_mask] = s1_preds[cloud_mask]
                correction_mask = (~cloud_mask) & low_conf_mask & (s1_coh < COHERENCE_THRESHOLD)
                final_preds[correction_mask] = 1 
                false_alarm_mask = (~cloud_mask) & low_conf_mask & (s2_preds == 1) & (s1_coh > 0.6)
                final_preds[false_alarm_mask] = 0
                
                # Nodata 掩膜
                nodata_mask = (b2 == 255) 
                s2_conf[nodata_mask] = 255
                
                # --- 写入模块 ---
                dst_class.write(final_preds, 1, window=window)
                dst_conf.write(s2_conf, 1, window=window)
                
                if SAVE_COHERENCE:
                    s1_coh_out = s1_coh.copy()
                    s1_coh_out[nodata_mask] = np.nan
                    dst_coh.write(s1_coh_out.astype(np.float32), 1, window=window)
                    
                # 写入云掩膜矩阵 (True=1, False=0)
                if SAVE_CLOUD_MASK:
                    cloud_out = cloud_mask.astype(np.uint8)
                    cloud_out[nodata_mask] = 255
                    dst_cloud.write(cloud_out, 1, window=window)

    print(f"✅ 硬分类结果生成完毕: {OUTPUT_FUSED_TIF}")
    print(f"✅ 模型置信度生成完毕: {OUTPUT_CONF_TIF}")
    if SAVE_COHERENCE:
        print(f"✅ 相干性图像生成完毕: {OUTPUT_COH_TIF}")
    if SAVE_CLOUD_MASK:
        print(f"✅ 云掩膜图像生成完毕: {OUTPUT_CLOUD_TIF}")
        
    return OUTPUT_FUSED_TIF

def extract_field_stats(fused_tif_path, gpkg_path, out_dir='./out'):
    print(f"提取地块级翻耕事件属性: {gpkg_path}")
    os.makedirs(out_dir, exist_ok=True)
    
    gdf = gpd.read_file(gpkg_path)
    stats = rs.zonal_stats(gdf, fused_tif_path, categorical=True, nodata=255, geo=False)
    
    dominant_status = [max(s, key=s.get) if isinstance(s, dict) and s else np.nan for s in stats]
    gdf['tillage_0921_1005'] = dominant_status
    
    base_name = os.path.basename(gpkg_path)
    new_name = base_name.replace('.gpkg', '_updated.gpkg')
    out_gpkg = os.path.join(out_dir, new_name)
    
    gdf.to_file(out_gpkg, driver='GPKG')
    print(f"✅ 管线运行成功，结果保存至: {out_gpkg}")

if __name__ == "__main__":
    aligned_t1 = S1_T1_RAW_PATH.replace('.tiff', '_aligned.tif')
    aligned_t2 = S1_T2_RAW_PATH.replace('.tiff', '_aligned.tif')
    
    if not os.path.exists(aligned_t1): align_s1_to_master(S1_T1_RAW_PATH, S2_PATH, aligned_t1)
    if not os.path.exists(aligned_t2): align_s1_to_master(S1_T2_RAW_PATH, S2_PATH, aligned_t2)
        
    fused_tif = process_and_fuse(aligned_t1, aligned_t2)
    extract_field_stats(fused_tif, CSB_FIELDS_GPKG)