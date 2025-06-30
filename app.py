import os
import pandas as pd
import numpy as np
from flask import Flask, request, render_template, send_file
from datetime import datetime

app = Flask(__name__)

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
        file_bc1 = request.files['file_bc1']
        file_bc2 = request.files['file_bc2']
        start = request.form['start_time']
        end = request.form['end_time']

        df_bc1 = pd.read_csv(file_bc1)
        df_bc2 = pd.read_csv(file_bc2)

        order = ['逆变B桥臂温度', '逆变A桥臂温度', '整流二极管温度',
                 '防反二极管温度', 'BD二极管温度', '充电机柜内温度', '进风口温度']

        result_bc1 = extract_max_temperatures(df_bc1, "BC1", start, end, order)
        result_bc2 = extract_max_temperatures(df_bc2, "BC2", start, end, order)

        combined = pd.concat([result_bc1, result_bc2])
        output_path = os.path.join("result.csv")
        combined.to_csv(output_path, index=False, encoding="utf-8-sig")
        return send_file(output_path, as_attachment=True)

    return render_template('index.html')

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
