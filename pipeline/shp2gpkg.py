import geopandas as gpd
import os

def convert_shp_to_gpkg(shp_path, gpkg_path, layer_name=None):
    """
    将 Shapefile 转换为单文件数据库 GeoPackage 格式。
    """
    if not os.path.exists(shp_path):
        raise FileNotFoundError(f"找不到输入文件: {shp_path}")
        
    print(f"正在读取 Shapefile: {shp_path} ...")
    # 步骤 1：将矢量数据读入内存 (GeoDataFrame)
    gdf = gpd.read_file(shp_path)

    # 步骤 2：确定图层名称（若未指定，则默认使用 GPKG 的文件名）
    if layer_name is None:
        layer_name = os.path.splitext(os.path.basename(gpkg_path))[0]

    print(f"正在导出为 GeoPackage (图层名: {layer_name}) ...")
    # 步骤 3：指定驱动为 GPKG 并导出
    gdf.to_file(gpkg_path, driver="GPKG", layer=layer_name)
    
    print(f"✅ 转换完成！输出文件位置: {gpkg_path}")

if __name__ == "__main__":
    # 在此处修改为你的实际文件路径
    INPUT_SHP = "./data/utils/ROI.shp"
    OUTPUT_GPKG = "./data/utils/ROI.gpkg"
    
    convert_shp_to_gpkg(INPUT_SHP, OUTPUT_GPKG)