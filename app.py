from flask import Flask, render_template, request, send_file
import pandas as pd
import os
import numpy as np
from io import BytesIO
from datetime import datetime

app = Flask(__name__)

# === 数据处理函数（你原来的逻辑） ===
def normalize_to_range(x, new_min=0.0, new_max=0.035):
    x_min = np.min(x)
    x_max = np.max(x)
    return new_min + (x - x_min) * (new_max - new_min) / (x_max - x_min)

def extract_max_temperatures(df, label, start_time_str, end_time_str, custom_order):
    df['时间'] = pd.to_datetime(df[['时', '分', '秒']].astype(str).agg(':'.join, axis=1), format="%H:%M:%S")
    start_time = pd.to_datetime(start_time_str, format="%H:%M:%S")
    end_time = pd.to_datetime(end_time_str, format="%H:%M:%S")
    df_filtered = df[(df["时间"] >= start_time) & (df["时间"] <= end_time)]
    temp_cols = [col for col in df_filtered.columns if "温度" in col]
    records = []
    for col in temp_cols:
        if df_filtered[col].isnull().all():
            continue
        max_idx = df_filtered[col].idxmax()
        max_value = df_filtered.loc[max_idx, col]
        max_time = df_filtered.loc[max_idx, "时间"]
        records.append({
            "测点名称": col,
            "最大温度": max_value,
            "出现时间": max_time.time(),
            "所属区域": label
        })
    df_out = pd.DataFrame(records)
    df_out["测点名称"] = pd.Categorical(df_out["测点名称"], categories=custom_order, ordered=True)
    return df_out.sort_values("测点名称")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        csv1 = request.files['csv1']
        csv2 = request.files['csv2']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        df1 = pd.read_csv(csv1)
        df2 = pd.read_csv(csv2)

        order = ['逆变B桥臂温度', '逆变A桥臂温度', '整流二极管温度',
                 '防反二极管温度', 'BD二极管温度', '充电机柜内温度', '进风口温度']

        df_bc1 = extract_max_temperatures(df1, "BC1", start_time, end_time, order)
        df_bc2 = extract_max_temperatures(df2, "BC2", start_time, end_time, order)

        output = pd.concat([df_bc1, df_bc2])

        output_stream = BytesIO()
        output.to_csv(output_stream, index=False, encoding='utf-8-sig')
        output_stream.seek(0)

        return send_file(output_stream, download_name="max_temperatures.csv", as_attachment=True)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
