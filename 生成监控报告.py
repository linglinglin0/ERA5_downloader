#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ERA5性能监控报告生成器
从数据库读取监控数据，生成HTML可视化报告

功能：
- 生成静态HTML报告
- 包含交互式图表
- 支持离线查看
"""

import os
import sqlite3
import json
from datetime import datetime
from pathlib import Path


class PerformanceReportGenerator:
    """性能报告生成器"""

    def __init__(self, db_path="era5_performance.db"):
        self.db_path = db_path

    def generate_html_report(self, output_path="era5_performance_report.html"):
        """生成HTML报告"""

        # 获取数据
        logs = self._get_all_logs()
        stats = self._get_statistics()

        if not logs:
            print("[错误] 没有监控数据")
            return False

        # 生成HTML
        html = self._create_html_template(logs, stats)

        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"[成功] 报告已生成: {output_path}")
        print(f"        数据点: {len(logs)} 个")
        return True

    def _get_all_logs(self):
        """获取所有日志"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp, datetime, download_speed, total_downloaded,
                           active_threads, cpu_usage, memory_usage, network_errors
                    FROM performance_logs
                    ORDER BY timestamp ASC
                ''')
                return cursor.fetchall()
        except Exception as e:
            print(f"[错误] 读取数据库失败: {e}")
            return []

    def _get_statistics(self):
        """获取统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 基本统计
                cursor.execute('''
                    SELECT
                        COUNT(*) as total_count,
                        AVG(download_speed) as avg_speed,
                        MAX(download_speed) as max_speed,
                        MIN(download_speed) as min_speed,
                        MAX(total_downloaded) as final_downloaded,
                        MIN(timestamp) as start_time,
                        MAX(timestamp) as end_time,
                        AVG(cpu_usage) as avg_cpu,
                        AVG(memory_usage) as avg_memory,
                        SUM(network_errors) as total_errors
                    FROM performance_logs
                ''')

                row = cursor.fetchone()
                return {
                    'total_count': row[0],
                    'avg_speed': row[1],
                    'max_speed': row[2],
                    'min_speed': row[3],
                    'final_downloaded': row[4],
                    'start_time': row[5],
                    'end_time': row[6],
                    'avg_cpu': row[7],
                    'avg_memory': row[8],
                    'total_errors': row[9]
                }
        except Exception as e:
            print(f"[错误] 统计失败: {e}")
            return {}

    def _create_html_template(self, logs, stats):
        """创建HTML模板"""

        # 准备图表数据
        timestamps = [log[0] * 1000 for log in logs]  # JavaScript使用毫秒
        speeds = [log[2] / (1024*1024) for log in logs]  # MB/s
        downloaded = [log[3] / (1024**3) for log in logs]  # GB
        cpu = [log[5] for log in logs]
        memory = [log[6] for log in logs]
        threads = [log[4] for log in logs]

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ERA5下载性能报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}

        .header p {{
            font-size: 14px;
            opacity: 0.9;
        }}

        .content {{
            padding: 30px;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}

        .stat-card h3 {{
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        }}

        .stat-card .value {{
            font-size: 28px;
            font-weight: bold;
            color: #333;
        }}

        .stat-card .unit {{
            font-size: 14px;
            color: #999;
        }}

        .chart-container {{
            margin-bottom: 30px;
        }}

        .chart-container h2 {{
            font-size: 20px;
            margin-bottom: 15px;
            color: #333;
        }}

        .chart-wrapper {{
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            height: 400px;
        }}

        .footer {{
            background: #f5f5f5;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ERA5下载性能监控报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>

        <div class="content">
            <!-- 统计卡片 -->
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>数据点数</h3>
                    <div class="value">{stats.get('total_count', 0)}</div>
                    <div class="unit">个</div>
                </div>
                <div class="stat-card">
                    <h3>平均速度</h3>
                    <div class="value">{stats.get('avg_speed', 0) / (1024*1024):.2f}</div>
                    <div class="unit">MB/s</div>
                </div>
                <div class="stat-card">
                    <h3>最高速度</h3>
                    <div class="value">{stats.get('max_speed', 0) / (1024*1024):.2f}</div>
                    <div class="unit">MB/s</div>
                </div>
                <div class="stat-card">
                    <h3>最低速度</h3>
                    <div class="value">{stats.get('min_speed', 0) / (1024*1024):.2f}</div>
                    <div class="unit">MB/s</div>
                </div>
                <div class="stat-card">
                    <h3>总下载量</h3>
                    <div class="value">{stats.get('final_downloaded', 0) / (1024**3):.2f}</div>
                    <div class="unit">GB</div>
                </div>
                <div class="stat-card">
                    <h3>平均CPU</h3>
                    <div class="value">{stats.get('avg_cpu', 0):.1f}</div>
                    <div class="unit">%</div>
                </div>
                <div class="stat-card">
                    <h3>平均内存</h3>
                    <div class="value">{stats.get('avg_memory', 0):.1f}</div>
                    <div class="unit">%</div>
                </div>
                <div class="stat-card">
                    <h3>网络错误</h3>
                    <div class="value">{stats.get('total_errors', 0)}</div>
                    <div class="unit">次</div>
                </div>
            </div>

            <!-- 图表 -->
            <div class="chart-container">
                <h2>下载速度趋势</h2>
                <div class="chart-wrapper">
                    <canvas id="speedChart"></canvas>
                </div>
            </div>

            <div class="chart-container">
                <h2>累计下载量</h2>
                <div class="chart-wrapper">
                    <canvas id="downloadedChart"></canvas>
                </div>
            </div>

            <div class="chart-container">
                <h2>系统资源使用</h2>
                <div class="chart-wrapper">
                    <canvas id="resourcesChart"></canvas>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>ERA5下载性能监控系统 v1.0.0</p>
            <p>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>

    <script>
        // 图表数据
        const timestamps = {json.dumps(timestamps)};
        const speeds = {json.dumps(speeds)};
        const downloaded = {json.dumps(downloaded)};
        const cpu = {json.dumps(cpu)};
        const memory = {json.dumps(memory)};
        const threads = {json.dumps(threads)};

        // 通用图表配置
        const commonOptions = {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{
                intersect: false,
                mode: 'index',
            }},
            plugins: {{
                legend: {{
                    display: true,
                    position: 'top',
                }},
                tooltip: {{
                    enabled: true,
                }},
            }},
        }};

        // 速度图表
        new Chart(document.getElementById('speedChart'), {{
            type: 'line',
            data: {{
                labels: timestamps,
                datasets: [{{
                    label: '下载速度 (MB/s)',
                    data: speeds,
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                }}],
            }},
            options: {{
                ...commonOptions,
                scales: {{
                    x: {{
                        type: 'time',
                        time: {{
                            displayFormats: {{
                                hour: 'HH:mm:ss'
                            }}
                        }},
                        title: {{
                            display: true,
                            text: '时间'
                        }}
                    }},
                    y: {{
                        title: {{
                            display: true,
                            text: '速度 (MB/s)'
                        }},
                        beginAtZero: true
                    }}
                }}
            }}
        }});

        // 下载量图表
        new Chart(document.getElementById('downloadedChart'), {{
            type: 'line',
            data: {{
                labels: timestamps,
                datasets: [{{
                    label: '累计下载量 (GB)',
                    data: downloaded,
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                }}],
            }},
            options: {{
                ...commonOptions,
                scales: {{
                    x: {{
                        type: 'time',
                        time: {{
                            displayFormats: {{
                                hour: 'HH:mm:ss'
                            }}
                        }},
                        title: {{
                            display: true,
                            text: '时间'
                        }}
                    }},
                    y: {{
                        title: {{
                            display: true,
                            text: '下载量 (GB)'
                        }},
                        beginAtZero: true
                    }}
                }}
            }}
        }});

        // 资源图表
        new Chart(document.getElementById('resourcesChart'), {{
            type: 'line',
            data: {{
                labels: timestamps,
                datasets: [
                    {{
                        label: 'CPU使用率 (%)',
                        data: cpu,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        pointRadius: 0,
                    }},
                    {{
                        label: '内存使用率 (%)',
                        data: memory,
                        borderColor: 'rgb(255, 206, 86)',
                        backgroundColor: 'rgba(255, 206, 86, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        pointRadius: 0,
                    }},
                    {{
                        label: '活跃连接数',
                        data: threads,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        pointRadius: 0,
                    }}
                ],
            }},
            options: {{
                ...commonOptions,
                scales: {{
                    x: {{
                        type: 'time',
                        time: {{
                            displayFormats: {{
                                hour: 'HH:mm:ss'
                            }}
                        }},
                        title: {{
                            display: true,
                            text: '时间'
                        }}
                    }},
                    y: {{
                        title: {{
                            display: true,
                            text: '使用率 (%)'
                        }},
                        beginAtZero: true,
                        max: 100
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

        return html


def main():
    """主函数"""
    print("=" * 60)
    print(" " * 15 + "ERA5性能报告生成器")
    print("=" * 60)
    print()

    generator = PerformanceReportGenerator()

    # 生成报告
    output_file = f"era5_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    if generator.generate_html_report(output_file):
        print()
        print("[提示] 在浏览器中打开报告文件查看")
        import os
        os.startfile(output_file)
    else:
        print("[失败] 报告生成失败")

    print()
    input("按Enter键退出...")


if __name__ == "__main__":
    main()
