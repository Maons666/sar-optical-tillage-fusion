import ee
import geopandas as gpd
from shapely.geometry import mapping
import warnings
warnings.filterwarnings('ignore')

# 初始化 GEE（请确保已通过认证）
ee.Initialize(project='ee-xwang') 

def get_s2_roi_export(roi_gpkg_path, start_date_str, end_date_str, drive_folder='Tillage_Export'):
    """基于本地 ROI 提取单周期 Sentinel-2 影像（精准多边形裁剪版）"""
    print(f"解析 ROI 多边形边界: {roi_gpkg_path}")
    gdf = gpd.read_file(roi_gpkg_path)
    
    # 1. 投影转换防错机制 (强制 WGS84 给 GEE 搜索用)
    if gdf.crs != 'EPSG:4326':
        print(f"检测到输入 CRS 为 {gdf.crs}，正在转换为 EPSG:4326...")
        gdf_wgs84 = gdf.to_crs('EPSG:4326')
    else:
        gdf_wgs84 = gdf
        
    # 2. 多边形融合与 GeoJSON 提取
    # unary_union 确保如果 GPKG 里有多个相邻的小多边形，会被合并成一个总的外部轮廓
    merged_geom = gdf_wgs84.geometry.unary_union
    geom_dict = mapping(merged_geom)  # 转化为标准的 GeoJSON 字典格式
    
    # 将字典传递给 GEE 构建精准多边形
    roi_geometry = ee.Geometry(geom_dict)
    
    print(f"设定 S2 合成时间区间: {start_date_str} 至 {end_date_str}")
    
    collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                  .filterDate(start_date_str, end_date_str)
                  .filterBounds(roi_geometry)
                  .sort('system:time_start', False))
    
    if collection.size().getInfo() == 0:
        raise ValueError(f"严重警告：该时间段 ({start_date_str} - {end_date_str}) 内无数据！")
        
    # 3. 镶嵌并执行精确的异形裁剪 (clip)
    mosaic = collection.mosaic()
    bands = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'SCL']
    
    # clip() 会将多边形外部的像素全部掩膜 (Mask) 掉，变为 NoData
    export_img = mosaic.select(bands).clip(roi_geometry).uint32()
    
    file_name = f"S2_ROI_mosaic_{start_date_str}_{end_date_str}"
    
    # 4. 导出配置 (输出端依然保持你的目标工作投影 EPSG:5070)
    task = ee.batch.Export.image.toDrive(
        image=export_img,
        description=file_name,
        folder=drive_folder,
        fileNamePrefix=file_name,
        scale=30,
        crs='EPSG:5070',  
        region=roi_geometry, # GEE 会根据多边形的极值自动生成 GeoTIFF 的矩形外框
        maxPixels=1e10,
        fileFormat='GeoTIFF'
    )
    task.start()
    print(f"✅ 精准多边形裁剪任务已提交: {file_name}")

if __name__ == "__main__":
    ROI_FILE = './data/utils/ROI.gpkg'
    START_DATE = '2025-09-14'
    END_DATE = '2025-09-21'
    get_s2_roi_export(ROI_FILE, START_DATE, END_DATE)