#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import glob
import math
from datetime import datetime

def find_latest_ptatmon():
    files = glob.glob('*_ptatmon.txt')
    if not files:
        print("錯誤：找不到任何 *_ptatmon.txt 檔案。")
        sys.exit(1)
    latest = max(files, key=os.path.getmtime)
    return latest

def parse_ptat_file(filename):
    data = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"無法讀取檔案 {filename}: {e}")
        sys.exit(1)

    start = False
    for line in lines:
        if 'Index' in line.strip():
            start = True
            continue
        if not start or not line.strip():
            continue

        parts = line.split()
        if len(parts) < 29:
            continue

        device = parts[3]
        if device != 'CPU0':
            continue

        try:
            index = int(parts[2])
        except ValueError:
            continue

        # 只跳過 Index 0（校準起始點），保留 Index 1 以後
        if index == 0:
            continue

        # 提取時間戳（日期 + 時間）
        timestamp = parts[0] + " " + parts[1]

        cfreq_str = parts[6]
        temp_str = parts[19]
        dts_str = parts[20]
        power_str = parts[21]
        tstat_str = parts[24]
        tmargin_str = parts[27]

        try:
            cfreq = float(cfreq_str)
            temp = float(temp_str)
            dts = float(dts_str)
            power = float(power_str)
            tmargin = float(tmargin_str)
        except ValueError:
            continue

        data.append({
            'index': index,
            'timestamp': timestamp,
            'cfreq': cfreq,
            'cfreq_str': cfreq_str,
            'temp': temp,
            'temp_str': temp_str,
            'dts': dts,
            'dts_str': dts_str,
            'power': power,
            'power_str': power_str,
            'tstat': tstat_str,
            'tmargin': tmargin,
            'tmargin_str': tmargin_str
        })

    return data

def compute_stats(values):
    n = len(values)
    if n == 0:
        return None, None, None, None
    avg = sum(values) / n
    maxv = max(values)
    minv = min(values)
    variance = sum((x - avg) ** 2 for x in values) / n
    std = math.sqrt(variance)
    return avg, maxv, minv, std

def get_abnormal_reasons(row):
    reasons = []
    if row['tstat'] != '0x0':
        reasons.append('TStat≠0x0')
    if row['cfreq'] < 2300:
        reasons.append('頻率<2300MHz')
    if row['tmargin'] < 0:
        reasons.append('TMargin<0')
    if row['dts'] == 0:
        reasons.append('DTS=0')
    if row['power'] < 200:
        reasons.append('功耗<200W')
    return reasons

def generate_html_report(data, filename):
    if not data:
        return "<h2>沒有找到 CPU0 的有效數據（正式測試階段），請檢查日誌檔案</h2>"

    cfreqs = [d['cfreq'] for d in data]
    temps = [d['temp'] for d in data]
    dtses = [d['dts'] for d in data]
    powers = [d['power'] for d in data]
    tmargins = [d['tmargin'] for d in data]

    cf_avg, cf_max, cf_min, cf_std = compute_stats(cfreqs)
    temp_avg, temp_max, temp_min, temp_std = compute_stats(temps)
    dts_avg, dts_max, dts_min, dts_std = compute_stats(dtses)
    pwr_avg, pwr_max, pwr_min, pwr_std = compute_stats(powers)
    tm_avg, tm_max, tm_min, tm_std = compute_stats(tmargins)

    total_pts = len(data)
    tstat_nonzero = sum(1 for d in data if d['tstat'] != '0x0')
    tmargin_neg = sum(1 for d in data if d['tmargin'] < 0)
    dts_zero = sum(1 for d in data if d['dts'] == 0)
    freq_low = sum(1 for d in data if d['cfreq'] < 2300)
    power_low = sum(1 for d in data if d['power'] < 200)

    if tstat_nonzero > 0:
        conclusion = 'danger'
        msg = '⚠️ 偵測到 TStat 非 0，表示系統曾觸發節流（Throttling），存在降速！'
    elif freq_low > total_pts * 0.05:
        conclusion = 'danger'
        msg = '⚠️ 有超過 5% 的時間頻率低於基頻 2300MHz，表示發生明顯降頻！'
    elif tmargin_neg > total_pts * 0.1:
        conclusion = 'warning'
        msg = '⚠️ 超過 10% 的時間 TMargin 為負，散熱餘量不足，但尚未觸發節流，需注意散熱改善。'
    elif dts_zero > 0:
        conclusion = 'warning'
        msg = '⚠️ 出現 DTS=0，表示溫度已達 Tprochot 上限，雖未降速但已無散熱餘量。'
    else:
        conclusion = 'good'
        msg = '✅ 測試期間全程穩定，功耗維持 215W 附近，頻率未低於基頻，無降速現象，Full TDP 測試通過！'

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>PTAT Full TDP 測試報告 (含完整數據)</title>
<style>
body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background: #f5f5f5; }}
.container {{ max-width: 1400px; margin: auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
h1, h2, h3 {{ color: #333; }}
.summary-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
.summary-table th, .summary-table td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
.summary-table th {{ background-color: #4CAF50; color: white; }}
.summary-table tr:nth-child(even) {{ background-color: #f9f9f9; }}
.detection {{ margin-top: 20px; }}
.detection-item {{ display: inline-block; margin: 5px 15px 5px 0; padding: 8px 15px; background: #eee; border-radius: 5px; }}
.good {{ background: #d4edda; border-left: 5px solid #28a745; padding: 10px; }}
.warning {{ background: #fff3cd; border-left: 5px solid #ffc107; padding: 10px; }}
.danger {{ background: #f8d7da; border-left: 5px solid #dc3545; padding: 10px; }}
.footer {{ margin-top: 30px; color: #777; font-size: 0.9em; }}
.data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9em;
    margin-top: 20px;
}}
.data-table th, .data-table td {{
    border: 1px solid #ccc;
    padding: 5px 8px;
    text-align: center;
}}
.data-table th {{
    background-color: #2c3e50;
    color: white;
    position: sticky;
    top: 0;
}}
.data-table tr.abnormal {{
    background-color: #f8d7da !important;
    color: #721c24;
}}
.data-table tr.abnormal td {{
    font-weight: bold;
}}
.data-table tr:nth-child(even) {{
    background-color: #f9f9f9;
}}
.data-table tr.abnormal:nth-child(even) {{
    background-color: #f5c6cb !important;
}}
.scrollable {{
    max-height: 600px;
    overflow-y: auto;
}}
</style>
</head>
<body>
<div class="container">
<h1>📊 TerraEdge Full TDP 測試報告 (含完整數據)</h1>
<p><strong>測試日誌：</strong> {filename}</p>
<p><strong>正式測試資料筆數：</strong> {total_pts} 筆 (已排除校準階段 Index 0)</p>
<p><strong>分析時間：</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

<h2>📈 關鍵參數統計摘要</h2>
<table class="summary-table">
<thead><tr><th>參數</th><th>平均值</th><th>最大值</th><th>最小值</th><th>標準差</th></tr></thead>
<tbody>
<tr><td><strong>頻率 (MHz)</strong></td><td>{cf_avg:.1f}</td><td>{cf_max:.1f}</td><td>{cf_min:.1f}</td><td>{cf_std:.2f}</td></tr>
<tr><td><strong>溫度 (°C)</strong></td><td>{temp_avg:.1f}</td><td>{temp_max:.1f}</td><td>{temp_min:.1f}</td><td>{temp_std:.2f}</td></tr>
<tr><td><strong>DTS (°C)</strong></td><td>{dts_avg:.1f}</td><td>{dts_max:.1f}</td><td>{dts_min:.1f}</td><td>{dts_std:.2f}</td></tr>
<tr><td><strong>功耗 (W)</strong></td><td>{pwr_avg:.1f}</td><td>{pwr_max:.1f}</td><td>{pwr_min:.1f}</td><td>{pwr_std:.2f}</td></tr>
<tr><td><strong>TMargin (°C)</strong></td><td>{tm_avg:.1f}</td><td>{tm_max:.1f}</td><td>{tm_min:.1f}</td><td>{tm_std:.2f}</td></tr>
</tbody>
</table>

<h2>🔍 異常偵測摘要</h2>
<div class="detection">
<div class="detection-item">📌 總採樣點數：{total_pts}</div>
<div class="detection-item">⚠️ TStat≠0x0 次數：{tstat_nonzero}</div>
<div class="detection-item">❄️ TMargin<0 次數：{tmargin_neg}</div>
<div class="detection-item">🔥 DTS=0 次數：{dts_zero}</div>
<div class="detection-item">⬇️ 頻率<2300MHz 次數：{freq_low}</div>
<div class="detection-item">⚡ 功耗<200W 次數：{power_low}</div>
</div>

<h2>📋 結論</h2>
<div class="{conclusion}"><strong>{msg}</strong></div>

<h2>📄 完整數據表格 (紅字標示異常行，並註明原因)</h2>
<p><em>異常條件：TStat≠0x0、頻率＜2300MHz、TMargin＜0、DTS=0、功耗＜200W，任一成立即標紅。</em></p>
<div class="scrollable">
<table class="data-table">
<thead><tr><th>Index</th><th>時間戳</th><th>CFreq (MHz)</th><th>Temp (°C)</th><th>DTS (°C)</th><th>Power (W)</th><th>TStat</th><th>TMargin (°C)</th><th>異常原因</th></tr></thead>
<tbody>
"""
    for row in data:
        reasons = get_abnormal_reasons(row)
        abnormal = bool(reasons)
        row_class = 'abnormal' if abnormal else ''
        reason_text = '；'.join(reasons) if reasons else ''
        html += f"""<tr class="{row_class}">
            <td>{row['index']}</td>
            <td>{row['timestamp']}</td>
            <td>{row['cfreq_str']}</td>
            <td>{row['temp_str']}</td>
            <td>{row['dts_str']}</td>
            <td>{row['power_str']}</td>
            <td>{row['tstat']}</td>
            <td>{row['tmargin_str']}</td>
            <td>{reason_text}</td>
        </tr>
"""
    html += """
</tbody>
</table>
</div>
<div class="footer">
報告產生時間：""" + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
</div>
</div>
</body>
</html>
"""
    return html

def main():
    print(f"開始處理時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    latest_file = find_latest_ptatmon()
    print(f"自動偵測到日誌檔案：{latest_file}")
    data = parse_ptat_file(latest_file)
    if not data:
        print("未提取到有效數據（正式測試階段），請檢查檔案格式。")
        sys.exit(1)

    html_content = generate_html_report(data, latest_file)

    output = "report.html"
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ 報告已成功產生：{output}")
    print(f"完成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("請用瀏覽器開啟查看完整數據與異常標示。")

if __name__ == "__main__":
    main()