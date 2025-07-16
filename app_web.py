import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, dash_table
import geopandas as gpd
#from shapely.geometry import Point
import plotly.graph_objects as go

import os
os.chdir(os.path.dirname(__file__))

with open("data/kaohsiung_region.geojson", encoding="utf-8") as f:
    geojson = json.load(f)
region_data = gpd.GeoDataFrame.from_features(geojson["features"])
region_data['centroid'] = region_data.geometry.centroid
region_data['centroid_lon'] = region_data['centroid'].x
region_data['centroid_lat'] = region_data['centroid'].y
label_col = 'TOWNNAME'

# 讀取點資料
df = pd.read_csv("data/KH_case_s3_20250627b.csv")  # 欄位應包含 lat, lon, name, info 等

#資料處理
df2 = pd.DataFrame(df['district'].value_counts()).reset_index()  # 將索引重置為普通列
df2.columns = ['district', 'count']  # 重命名列

# 建立地圖 figure
# === 1. 建立 Choroplethmap 行政區多邊形 ===
fig = go.Figure(go.Choroplethmap(
    geojson=geojson,
    locations=region_data.index,
    z=[1] * len(region_data),  # Dummy 值
    showscale=False,
    hoverinfo='skip',
    marker_opacity=0.3,
    marker_line_width=1,
    marker_line_color='black',
))

# === 2. 加上行政區名稱文字（在 centroid 標註）===
fig.add_trace(go.Scattermap(
    lat=region_data['centroid_lat'],
    lon=region_data['centroid_lon'],
    mode='text',
    hoverinfo='skip',
    text=region_data[label_col],
    textfont=dict(size=12, color='black'),
    showlegend=False
))

# === 3. 加上個案點位資料 ===
fig.add_trace(go.Scattermap(
    lat=df['lat'],
    lon=df['lon'],
    mode='markers',
    marker=dict(size=8, color='gray'),
    #text=df.apply(lambda row: f"個案：{row['case']}<br>行政區：{row['district']}", axis=1),
    text=df['case'],
    
    customdata=df.apply(lambda row: [row['url'], row['district'], row['firm']], axis=1),  # 添加 url 和 district 到 customdata
    hoverinfo='text',
    name='個案',
))

# === 4. 地圖設定（改用 map_ 開頭） ===
fig.update_layout(
    map_style="carto-positron",  
    map_zoom=10,
    map_center={"lat": 22.623, "lon": 120.32},
    margin={"r": 0, "t": 0, "l": 0, "b": 0}
)

fig.show()

# 建立 Dash app
app = Dash(__name__)
'''
app.layout = html.Div([
    html.Div([
        dcc.Graph(id="map", figure=fig),  # 地圖
    ], style={"width": "70%", "display": "inline-block", "verticalAlign": "top"}),  # 左側區塊

    html.Div([
        html.Div(id="info-box", style={"marginTop": "20px", "fontSize": "18px"}),  # 顯示點擊的資訊
        html.Button("顯示資訊", id="info-button", style={"marginTop": "20px"}),  # 按鈕
        html.Div(id="info-output", style={"marginTop": "20px", "fontSize": "16px"}),  # 顯示按鈕輸出
    ], style={"width": "30%", "display": "inline-block", "verticalAlign": "top"}),  # 右側區塊
])
'''
app.layout = html.Div([
    html.H1("高都觀測站 Dashboard", style={"textAlign": "left", "marginBottom": "15px"}),  # 新增標題
    html.Div([
        dcc.Graph(id="map", figure=fig, style={"height": "80vh"}),  # 地圖
    ], style={"width": "70%", "display": "inline-block", "verticalAlign": "top"}),  # 左側區塊

    html.Div([
        html.Div([
            html.Div(id="info-box", style={"marginTop": "20px", "fontSize": "18px"}),  # 顯示點擊的資訊
            #html.Button("顯示資訊", id="info-button", style={"marginTop": "20px"}),  # 按鈕
        ], style={"height": "50%", "borderBottom": "1px solid #ccc"}),  # 上半部分

        html.Div([
            html.H2("透過過濾建商更新地圖、呈現該區有什麼其他建案", style={"textAlign": "left", "marginBottom": "13px"}),  # 開發中
            html.Div(id="extra-info", style={"marginTop": "20px", "fontSize": "16px"}),  # 顯示額外資訊
            html.Button("額外功能按鈕", id="extra-button", style={"marginTop": "20px"}),  # 額外按鈕
            #dash_table.DataTable(
            #    df2.to_dict('records'),  # 確保 df 中有這些欄位
            #    style_table={'height': '100%', 'overflowY': 'auto'},  # 增加樣式以防止表格溢出
            #    style_cell={'textAlign': 'left', 'fontSize': '14px'}  # 設定表格文字樣式
            #)

            dash_table.DataTable(
                id="firm_table",  # 新增唯一的 ID
                columns=[{"name": "建商", "id": "firm"}, {"name": "建案", "id": "case_name"}],  # 定義表格的列
                style_table={'height': '100%', 'overflowY': 'auto'},  # 增加樣式以防止表格溢出
                style_cell={'textAlign': 'left', 'fontSize': '14px'}  # 設定表格文字樣式
            )
        ], style={"height": "50%"}),  # 下半部分
    ], style={"width": "30%", "display": "inline-block", "verticalAlign": "top"}),  # 右側區塊
])



# 加入互動 callback
@app.callback(
    Output("info-output", "children"),
    Input("info-button", "n_clicks"),
    State("info-box", "children")
)

@app.callback(
    Output("firm_table", "data"),
    Input("map", "clickData")
)

def update_firm_info(click_data):
    if click_data is None:
        return []  # 如果沒有點擊事件，返回空列表

    try:
        point_info = click_data["points"][0]
        customdata = point_info.get("customdata", ["無相關連結", "未有資料", "未有資料"])
        empty_data = {"firm":"無資料", "case_name":"無資料"}
        # 確保 customdata 有足夠的值
        #if len(customdata) < 3:
        #    return []

        firm = customdata[2]  # 第三個值是 firm
        
        # 確保 df 中有 'firm' 欄位
        if "firm" not in df.columns:
            return empty_data

        result = df[df["firm"] == firm]
        result = result[["firm", "case_name"]]  # 只保留 district 和 firm 欄位，並去除重複值
        return result.to_dict('records')  # 回傳字典列表
        
    except Exception as e:
        print(f"Error in update_firm_info: {e}")
        return empty_data  # 如果發生錯誤，返回空列表


@app.callback(
    Output("info-box", "children"),
    Input("map", "clickData")
)

def update_info_box(click_data):
    if click_data is None:
        return "尚未點擊地圖上的點"
    
    point_info = click_data["points"][0]
    name = point_info.get("text", "未知名稱")
    lat = point_info.get("lat", "未知緯度")
    lon = point_info.get("lon", "未知經度")

    customdata = point_info.get("customdata", ["無相關連結", "未有資料","未有資料"])
    url = customdata[0]  # 第一個值是 url
    district = customdata[1]  # 第二個值是 district
    
    return html.Div([
        html.P(f"點擊的點資訊：", style={"fontSize": "22px"}),
        html.P(f"名稱：{name}", style={"fontSize": "12px"}),
        html.P(f"行政區：{district}", style={"fontSize": "12px"}),
        html.P(f"緯度：{lat:.4f}", style={"fontSize": "12px"}),
        html.P(f"經度：{lon:.4f}", style={"fontSize": "12px"}),
        html.A('點我開啟相簿', style={"fontSize": "12px"}, href=url, target="_blank") if url else "無"
    ])




def display_info(n_clicks, info_box_content):
    if n_clicks is None or n_clicks == 0:
        return "尚未點擊按鈕"
    return f"按鈕已被點擊，顯示資訊：{info_box_content}"

# 啟動本機伺服器
#程式會自行設置http://127.0.0.1:8050作為本地伺服器
if __name__ == "__main__":
    #app.run(debug=True)
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port)
    #app.run(debug=True, use_reloader=False, dev_tools_ui=False,port=8050)


