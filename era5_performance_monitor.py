#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ERA5下载性能监控工具
实时监控下载性能，绘制动态图表

功能：
1. 实时速度监控（折线图）
2. 累计下载量监控（折线图）
3. 数据持久化存储
4. 统计分析报告
5. 异常检测和告警
"""

import os
import sys
import time
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from collections import deque
import psutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import customtkinter as ctk

# 设置matplotlib中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 设置外观
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


# ================= 数据库管理 =================

class PerformanceDatabase:
    """性能数据库管理"""

    def __init__(self, db_path="era5_performance.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL UNIQUE,
                    datetime TEXT,
                    download_speed REAL,
                    total_downloaded REAL,
                    active_threads INTEGER,
                    cpu_usage REAL,
                    memory_usage REAL,
                    network_errors INTEGER
                )
            ''')

            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON performance_logs(timestamp)
            ''')

            conn.commit()

    def insert_log(self, timestamp, datetime_str, download_speed,
                   total_downloaded, active_threads, cpu_usage,
                   memory_usage, network_errors):
        """插入性能日志"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO performance_logs
                        (timestamp, datetime, download_speed, total_downloaded,
                         active_threads, cpu_usage, memory_usage, network_errors)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (timestamp, datetime_str, download_speed,
                          total_downloaded, active_threads, cpu_usage,
                          memory_usage, network_errors))
                    conn.commit()
            except Exception as e:
                print(f"[DB] 插入失败: {e}")

    def get_recent_logs(self, minutes=30):
        """获取最近的日志"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cutoff_time = time.time() - (minutes * 60)

                    cursor.execute('''
                        SELECT timestamp, datetime, download_speed, total_downloaded,
                               active_threads, cpu_usage, memory_usage, network_errors
                        FROM performance_logs
                        WHERE timestamp >= ?
                        ORDER BY timestamp ASC
                    ''', (cutoff_time,))

                    return cursor.fetchall()
            except Exception as e:
                print(f"[DB] 查询失败: {e}")
                return []

    def get_all_logs(self):
        """获取所有日志"""
        with self.lock:
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
                print(f"[DB] 查询失败: {e}")
                return []

    def get_statistics(self):
        """获取统计信息"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()

                    # 总记录数
                    cursor.execute('SELECT COUNT(*) FROM performance_logs')
                    total_count = cursor.fetchone()[0]

                    if total_count == 0:
                        return None

                    # 统计信息
                    cursor.execute('''
                        SELECT
                            AVG(download_speed) as avg_speed,
                            MAX(download_speed) as max_speed,
                            MIN(download_speed) as min_speed,
                            MAX(total_downloaded) as final_downloaded,
                            MIN(timestamp) as start_time,
                            MAX(timestamp) as end_time
                        FROM performance_logs
                    ''')

                    row = cursor.fetchone()
                    return {
                        'total_records': total_count,
                        'avg_speed': row[0],
                        'max_speed': row[1],
                        'min_speed': row[2],
                        'final_downloaded': row[3],
                        'start_time': row[4],
                        'end_time': row[5]
                    }
            except Exception as e:
                print(f"[DB] 统计失败: {e}")
                return None


# ================= 性能数据采集器 =================

class PerformanceCollector:
    """性能数据采集器"""

    def __init__(self, download_dir=None, process_name=None):
        self.download_dir = download_dir
        self.process_name = process_name or "python"
        self.process = None

        # ✅ 网络接口监控
        self.network_interfaces = []
        self.last_bytes_recv = 0
        self.last_net_time = time.time()
        self.first_net_collection = True

        # ✅ 下载文件大小监控（备用）
        self.initial_size = 0
        self.last_size = 0
        self.last_time = time.time()
        self.first_file_collection = True

        # ✅ 速度滑动平均
        self.speed_history = deque(maxlen=10)
        self.last_valid_speed = 0

        # ✅ 网络错误统计
        self.network_errors = 0
        self.error_log_path = "download_errors.log"

        # 初始化网络统计
        self._init_network_stats()

        # 初始化文件大小监控（备用）
        self._find_process()
        self._calculate_initial_size()

    def _init_network_stats(self):
        """初始化网络统计"""
        try:
            # 获取所有网络接口的I/O统计
            net_io = psutil.net_io_counters(pernic=True)

            # 找到活跃的网络接口（非回环，非虚拟）
            total_recv = 0

            for interface, stats in net_io.items():
                # 过滤掉回环接口和虚拟接口
                if interface.startswith('Loopback') or interface.startswith('vEthernet'):
                    continue

                # 只关注有接收流量的接口
                if stats.bytes_recv > 0 or stats.bytes_sent > 0:
                    self.network_interfaces.append({
                        'name': interface,
                        'last_recv': stats.bytes_recv,
                        'last_sent': stats.bytes_sent
                    })
                    total_recv += stats.bytes_recv

            # 记录初始接收字节数
            self.last_bytes_recv = total_recv
            self.last_net_time = time.time()

            # 打印找到的网络接口
            if self.network_interfaces:
                interfaces_str = ', '.join([iface['name'] for iface in self.network_interfaces[:5]])
                print(f"[Collector] 监控网络接口: {interfaces_str}")
                print(f"[Collector] 初始接收字节: {total_recv / (1024**2):.2f} MB")
            else:
                print("[Collector] 警告: 未找到活跃的网络接口")

        except Exception as e:
            print(f"[Collector] 网络监控初始化失败: {e}")
            print("[Collector] 将使用文件大小监控")
            self.network_interfaces = []

    def _find_process(self):
        """查找下载进程"""
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('ERA5download_GUI' in str(c) for c in cmdline):
                    self.process = proc
                    self.process_name = proc.info['name']
                    print(f"[Collector] 找到下载进程: PID={proc.pid}")
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        print(f"[Collector] 未找到下载进程，将监控系统整体")

    def _calculate_initial_size(self):
        """计算初始下载大小（包括.nc和.tmp文件）"""
        print(f"[Collector] 正在计算初始大小...")
        print(f"[Collector] 下载目录: {self.download_dir}")

        if self.download_dir and os.path.exists(self.download_dir):
            nc_count = 0
            tmp_count = 0
            for root, dirs, files in os.walk(self.download_dir):
                for file in files:
                    # ✅ 同时计算 .nc 和 .tmp 文件
                    if file.endswith('.nc') or file.endswith('.tmp'):
                        try:
                            size = os.path.getsize(os.path.join(root, file))
                            self.initial_size += size
                            if file.endswith('.nc'):
                                nc_count += 1
                            elif file.endswith('.tmp'):
                                tmp_count += 1
                        except:
                            pass

            print(f"[Collector] 找到 {nc_count} 个 .nc 文件, {tmp_count} 个 .tmp 文件")
            print(f"[Collector] 初始大小: {self.initial_size / (1024**2):.2f} MB "
                  f"({self.initial_size / (1024**3):.2f} GB)")
        else:
            print(f"[Collector] 目录不存在: {self.download_dir}")

        self.last_size = self.initial_size

    def collect(self):
        """采集当前性能数据"""
        current_time = time.time()
        timestamp = current_time
        datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # ✅ 优先使用网络接口监控
        download_speed, downloaded_bytes = self._get_network_speed(current_time)

        # ✅ 如果网络监控不可用，回退到文件大小监控
        if download_speed == 0 and len(self.speed_history) == 0:
            download_speed, downloaded_bytes = self._get_file_speed(current_time)

        # 系统资源使用
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_usage = psutil.virtual_memory().percent

        # 活跃线程数（估算）
        active_threads = self._estimate_active_threads()

        # 网络错误数
        network_errors = self._count_network_errors()

        return {
            'timestamp': timestamp,
            'datetime': datetime_str,
            'download_speed': download_speed,  # bytes/s
            'total_downloaded': downloaded_bytes,  # bytes
            'active_threads': active_threads,
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'network_errors': network_errors
        }

    def _get_network_speed(self, current_time):
        """✅ 基于网络接口I/O统计计算下载速度"""
        if not self.network_interfaces:
            return 0, 0

        try:
            # 获取当前网络统计
            net_io = psutil.net_io_counters(pernic=True)

            # 计算总接收字节
            total_recv = 0
            for interface in self.network_interfaces:
                if interface['name'] in net_io:
                    total_recv += net_io[interface['name']].bytes_recv

            # 计算增量和时间
            bytes_recv_delta = total_recv - self.last_bytes_recv
            time_elapsed = current_time - self.last_net_time

            # ✅ 首次网络采集
            if self.first_net_collection:
                self.last_net_time = current_time
                self.last_bytes_recv = total_recv
                self.first_net_collection = False
                if len(self.speed_history) <= 5:
                    print(f"[Collector] 首次网络采集 - 初始接收: {total_recv / (1024**2):.2f} MB")
                return 0, 0

            # ✅ 确保至少有1秒间隔
            if time_elapsed >= 1.0 and bytes_recv_delta > 0:
                instant_speed = bytes_recv_delta / time_elapsed

                # 使用滑动平均
                self.speed_history.append(instant_speed)
                valid_speeds = [s for s in self.speed_history if s > 0]

                if valid_speeds:
                    download_speed = sum(valid_speeds) / len(valid_speeds)
                    self.last_valid_speed = download_speed

                    # 调试输出（前5次）
                    if len(self.speed_history) <= 5:
                        print(f"[Collector] 网络 - 接收增量: {bytes_recv_delta / 1024:.1f} KB, "
                              f"速度: {download_speed / 1024:.2f} KB/s")
                else:
                    download_speed = self.last_valid_speed

                # 更新基准
                self.last_bytes_recv = total_recv
                self.last_net_time = current_time

                # 估算已下载量（基于网络流量）
                estimated_downloaded = total_recv - (self.initial_size if hasattr(self, 'initial_size') else 0)
                return download_speed, estimated_downloaded
            else:
                # 时间间隔太短或无增量
                return self.last_valid_speed, (total_recv if hasattr(self, 'initial_size') else 0)

        except Exception as e:
            print(f"[Collector] 网络监控失败: {e}")
            return 0, 0

    def _get_file_speed(self, current_time):
        """✅ 备用：基于文件大小计算下载速度"""
        current_size = self._get_current_size()
        downloaded_bytes = current_size - self.initial_size
        time_elapsed = current_time - self.last_time

        # ✅ 首次文件采集
        if self.first_file_collection:
            self.last_time = current_time
            self.last_size = current_size
            self.first_file_collection = False
            return 0, downloaded_bytes

        # ✅ 确保至少有1秒的时间间隔
        if time_elapsed >= 1.0:
            instant_speed = (current_size - self.last_size) / time_elapsed

            if instant_speed > 0:
                self.speed_history.append(instant_speed)
                valid_speeds = [s for s in self.speed_history if s > 0]

                if valid_speeds:
                    download_speed = sum(valid_speeds) / len(valid_speeds)
                    self.last_valid_speed = download_speed
                else:
                    download_speed = self.last_valid_speed
            else:
                download_speed = self.last_valid_speed if self.last_valid_speed > 0 else instant_speed

            self.last_size = current_size
            self.last_time = current_time

            # 调试输出
            if len(self.speed_history) <= 3:
                print(f"[Collector] 文件 - 增量: {(current_size - self.last_size) / 1024:.1f} KB, "
                      f"速度: {download_speed / 1024:.2f} KB/s")

            return download_speed, downloaded_bytes
        else:
            return self.last_valid_speed, downloaded_bytes

    def _get_current_size(self):
        """获取当前下载大小（包括.nc和.tmp文件）"""
        if not self.download_dir or not os.path.exists(self.download_dir):
            return 0

        current_size = 0
        for root, dirs, files in os.walk(self.download_dir):
            for file in files:
                # ✅ 同时监控 .nc（已完成）和 .tmp（下载中）文件
                if file.endswith('.nc') or file.endswith('.tmp'):
                    try:
                        current_size += os.path.getsize(
                            os.path.join(root, file)
                        )
                    except:
                        pass

        return current_size

    def _estimate_active_threads(self):
        """估算活跃线程数"""
        try:
            connections = psutil.net_connections()
            s3_connections = [
                c for c in connections
                if c.status == 'ESTABLISHED' and
                (c.raddr and ('52.218' in str(c.raddr.ip) or 's3' in str(c.raddr.ip).lower()))
            ]
            return len(s3_connections)
        except:
            return 0

    def _count_network_errors(self):
        """统计网络错误"""
        if not os.path.exists(self.error_log_path):
            return 0

        try:
            with open(self.error_log_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 统计最近的错误
                errors = content.count('ConnectionError')
                errors += content.count('ReadTimeout')
                errors += content.count('503')
                errors += content.count('429')
                return errors
        except:
            return 0


# ================= 主监控GUI =================

class PerformanceMonitorApp(ctk.CTk):
    """性能监控主界面"""

    def __init__(self):
        super().__init__()

        self.title("ERA5下载性能监控器")
        self.geometry("1400x900")

        # 数据库
        self.db = PerformanceDatabase()

        # 采集器
        self.collector = None

        # 监控状态
        self.is_monitoring = False
        self.monitor_thread = None
        self.update_interval = 2  # 2秒更新一次

        # 数据缓存（用于图表）
        self.max_points = 1000  # 最多显示1000个数据点

        # 构建界面
        self._build_ui()

        # 加载历史数据
        self._load_historical_data()

    def _build_ui(self):
        """构建界面"""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ================= 左侧控制面板 =================
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")

        # 标题
        ctk.CTkLabel(self.sidebar, text="性能监控器",
                     font=("微软雅黑", 20, "bold")).pack(pady=20)

        # 下载目录设置
        ctk.CTkLabel(self.sidebar, text="下载目录:", anchor="w").pack(
            fill="x", padx=20, pady=(10, 0)
        )
        self.dir_entry = ctk.CTkEntry(self.sidebar)
        self.dir_entry.pack(fill="x", padx=20, pady=5)

        browse_btn = ctk.CTkButton(self.sidebar, text="浏览...",
                                   command=self.select_directory)
        browse_btn.pack(fill="x", padx=20, pady=5)

        # 更新间隔
        ctk.CTkLabel(self.sidebar, text="更新间隔（秒）:").pack(
            fill="x", padx=20, pady=(20, 0)
        )
        self.interval_slider = ctk.CTkSlider(self.sidebar, from_=1, to=10,
                                             number_of_steps=9,
                                             command=self.on_interval_change)
        self.interval_slider.pack(fill="x", padx=20, pady=5)
        self.interval_slider.set(2)
        self.interval_label = ctk.CTkLabel(self.sidebar, text="2 秒")
        self.interval_label.pack(padx=20)

        # 数据范围
        ctk.CTkLabel(self.sidebar, text="显示时间范围:").pack(
            fill="x", padx=20, pady=(20, 0)
        )
        self.time_range_var = ctk.StringVar(value="30")
        time_range_menu = ctk.CTkOptionMenu(
            self.sidebar,
            variable=self.time_range_var,
            values=["10", "30", "60", "120", "全部"],
            command=self.on_time_range_change
        )
        time_range_menu.pack(fill="x", padx=20, pady=5)

        # 控制按钮
        self.start_btn = ctk.CTkButton(self.sidebar, text="开始监控",
                                       command=self.start_monitoring,
                                       fg_color="#1f6aa5",
                                       height=40)
        self.start_btn.pack(fill="x", padx=20, pady=(30, 10))

        self.stop_btn = ctk.CTkButton(self.sidebar, text="停止监控",
                                      command=self.stop_monitoring,
                                      fg_color="#a51f1f",
                                      height=40,
                                      state="disabled")
        self.stop_btn.pack(fill="x", padx=20, pady=5)

        # 导出按钮
        export_btn = ctk.CTkButton(self.sidebar, text="导出数据",
                                   command=self.export_data,
                                   height=40)
        export_btn.pack(fill="x", padx=20, pady=5)

        # ================= 实时统计面板 =================
        stats_frame = ctk.CTkFrame(self.sidebar)
        stats_frame.pack(fill="x", padx=20, pady=(30, 10))

        ctk.CTkLabel(stats_frame, text="实时统计",
                     font=("微软雅黑", 14, "bold")).pack(pady=10)

        self.speed_label = ctk.CTkLabel(stats_frame, text="当前速度: --",
                                        font=("Consolas", 12))
        self.speed_label.pack(anchor="w", padx=10)

        self.downloaded_label = ctk.CTkLabel(stats_frame, text="已下载: --",
                                             font=("Consolas", 12))
        self.downloaded_label.pack(anchor="w", padx=10)

        self.time_label = ctk.CTkLabel(stats_frame, text="运行时间: --",
                                       font=("Consolas", 12))
        self.time_label.pack(anchor="w", padx=10)

        self.errors_label = ctk.CTkLabel(stats_frame, text="网络错误: --",
                                         font=("Consolas", 12))
        self.errors_label.pack(anchor="w", padx=10)

        # ================= 右侧图表区域 =================
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        # 标题
        header_frame = ctk.CTkFrame(self.main_frame)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(header_frame, text="下载性能监控",
                     font=("微软雅黑", 16, "bold")).pack(side="left")

        self.status_label = ctk.CTkLabel(header_frame, text="未开始",
                                         text_color="gray")
        self.status_label.pack(side="right")

        # 图表容器
        self.notebook = ctk.CTkTabview(self.main_frame)
        self.notebook.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)

        # Tab 1: 速度监控
        self.tab_speed = self.notebook.add("下载速度")
        self._create_speed_chart()

        # Tab 2: 累计下载量
        self.tab_downloaded = self.notebook.add("累计下载量(GB/MB)")
        self._create_downloaded_chart()

        # Tab 3: 系统资源
        self.tab_resources = self.notebook.add("系统资源")
        self._create_resources_chart()

        # Tab 4: 统计分析
        self.tab_stats = self.notebook.add("统计分析")
        self._create_stats_view()

    def _create_speed_chart(self):
        """创建速度图表"""
        self.fig_speed = Figure(figsize=(10, 4), dpi=100)
        self.ax_speed = self.fig_speed.add_subplot(111)

        self.ax_speed.set_title("下载速度", fontsize=12, fontweight='bold')
        self.ax_speed.set_xlabel("时间", fontsize=10)
        self.ax_speed.set_ylabel("速度 (MB/s)", fontsize=10)
        self.ax_speed.grid(True, alpha=0.3)

        # ✅ 设置Y轴从0开始，避免负值
        self.ax_speed.set_ylim(bottom=0)

        self.line_speed, = self.ax_speed.plot([], [], 'b-', linewidth=2, label='下载速度')
        self.ax_speed.legend(loc='upper right')

        # 时间格式化
        self.ax_speed.xaxis.set_major_formatter(
            mdates.DateFormatter('%H:%M:%S')
        )
        self.fig_speed.autofmt_xdate()

        self.canvas_speed = FigureCanvasTkAgg(self.fig_speed, master=self.tab_speed)
        self.canvas_speed.get_tk_widget().pack(fill="both", expand=True)

    def _create_downloaded_chart(self):
        """创建累计下载量图表"""
        self.fig_downloaded = Figure(figsize=(10, 4), dpi=100)
        self.ax_downloaded = self.fig_downloaded.add_subplot(111)

        self.ax_downloaded.set_title("累计下载量", fontsize=12, fontweight='bold')
        self.ax_downloaded.set_xlabel("时间", fontsize=10)

        # ✅ 创建双Y轴：左轴GB，右轴MB
        self.ax_downloaded_gb = self.ax_downloaded
        self.ax_downloaded_mb = self.ax_downloaded.twinx()

        self.ax_downloaded_gb.set_ylabel("下载量 (GB)", color='g', fontsize=10)
        self.ax_downloaded_mb.set_ylabel("下载量 (MB)", color='orange', fontsize=10)

        self.ax_downloaded_gb.grid(True, alpha=0.3)
        self.ax_downloaded_gb.set_ylim(bottom=0)
        self.ax_downloaded_mb.set_ylim(bottom=0)

        self.line_downloaded, = self.ax_downloaded_gb.plot(
            [], [], 'g-', linewidth=2, label='累计下载(GB)'
        )

        # 时间格式化
        self.ax_downloaded_gb.xaxis.set_major_formatter(
            mdates.DateFormatter('%H:%M:%S')
        )
        self.fig_downloaded.autofmt_xdate()

        self.canvas_downloaded = FigureCanvasTkAgg(self.fig_downloaded, master=self.tab_downloaded)
        self.canvas_downloaded.get_tk_widget().pack(fill="both", expand=True)

    def _create_resources_chart(self):
        """创建系统资源图表"""
        self.fig_resources = Figure(figsize=(10, 4), dpi=100)
        self.ax_resources = self.fig_resources.add_subplot(111)

        self.ax_resources.set_title("系统资源使用率", fontsize=12, fontweight='bold')
        self.ax_resources.set_xlabel("时间", fontsize=10)
        self.ax_resources.set_ylabel("使用率 (%)", fontsize=10)
        self.ax_resources.set_ylim(0, 100)
        self.ax_resources.grid(True, alpha=0.3)

        self.line_cpu, = self.ax_resources.plot([], [], 'r-', linewidth=2, label='CPU')
        self.line_memory, = self.ax_resources.plot([], [], 'y-', linewidth=2, label='内存')
        self.line_threads, = self.ax_resources.plot([], [], 'c-', linewidth=2, label='活跃连接')
        self.ax_resources.legend(loc='upper right')

        # 时间格式化
        self.ax_resources.xaxis.set_major_formatter(
            mdates.DateFormatter('%H:%M:%S')
        )
        self.fig_resources.autofmt_xdate()

        self.canvas_resources = FigureCanvasTkAgg(self.fig_resources, master=self.tab_resources)
        self.canvas_resources.get_tk_widget().pack(fill="both", expand=True)

    def _create_stats_view(self):
        """创建统计视图"""
        stats_container = ctk.CTkScrollableFrame(self.tab_stats)
        stats_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.stats_text = ctk.CTkTextbox(stats_container, font=("Consolas", 11))
        self.stats_text.pack(fill="both", expand=True)

    def select_directory(self):
        """选择下载目录"""
        from tkinter import filedialog
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, directory)

    def on_interval_change(self, value):
        """更新间隔变化"""
        self.update_interval = int(value)
        self.interval_label.configure(text=f"{self.update_interval} 秒")

    def on_time_range_change(self, choice):
        """时间范围变化"""
        self._update_charts()

    def start_monitoring(self):
        """开始监控"""
        download_dir = self.dir_entry.get().strip()

        if not download_dir or not os.path.exists(download_dir):
            from tkinter import messagebox
            messagebox.showerror("错误", "请选择有效的下载目录")
            return

        # 初始化采集器
        self.collector = PerformanceCollector(download_dir=download_dir)

        self.is_monitoring = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(text="监控中...", text_color="#00e676")

        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        # 启动UI更新
        self._update_ui()

    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="已停止", text_color="orange")

    def _monitor_loop(self):
        """监控循环（后台线程）"""
        while self.is_monitoring:
            try:
                # 采集数据
                data = self.collector.collect()

                # 存入数据库
                self.db.insert_log(
                    timestamp=data['timestamp'],
                    datetime_str=data['datetime'],
                    download_speed=data['download_speed'],
                    total_downloaded=data['total_downloaded'],
                    active_threads=data['active_threads'],
                    cpu_usage=data['cpu_usage'],
                    memory_usage=data['memory_usage'],
                    network_errors=data['network_errors']
                )

                # 等待下一次采集
                time.sleep(self.update_interval)

            except Exception as e:
                print(f"[Monitor] 采集失败: {e}")
                time.sleep(self.update_interval)

    def _update_ui(self):
        """更新UI（主线程）"""
        if not self.is_monitoring:
            return

        # 更新图表
        self._update_charts()

        # 更新统计面板
        self._update_stats_panel()

        # 继续更新
        self.after(2000, self._update_ui)

    def _update_charts(self):
        """更新所有图表"""
        # 获取数据
        time_range = self.time_range_var.get()

        if time_range == "全部":
            logs = self.db.get_all_logs()
        else:
            logs = self.db.get_recent_logs(minutes=int(time_range))

        if not logs:
            return

        # 解析数据
        timestamps = []
        speeds = []
        downloaded_gb = []
        downloaded_mb = []
        cpu = []
        memory = []
        threads = []

        for log in logs:
            ts = log[0]
            dt = datetime.fromtimestamp(ts)
            timestamps.append(dt)
            speeds.append(log[2] / (1024*1024))  # MB/s
            downloaded_gb.append(log[3] / (1024**3))  # GB
            downloaded_mb.append(log[3] / (1024*1024))  # MB
            cpu.append(log[5])
            memory.append(log[6])
            threads.append(log[4] * 10)  # 放大10倍以便显示

        # 更新速度图表
        if timestamps and speeds:
            self.line_speed.set_data(timestamps, speeds)
            self.ax_speed.relim()
            self.ax_speed.autoscale_view()
            # 确保Y轴从0开始
            ymin, ymax = self.ax_speed.get_ylim()
            if ymin < 0:
                self.ax_speed.set_ylim(bottom=0)
            self.canvas_speed.draw()

        # ✅ 更新下载量图表（双Y轴）
        if timestamps and downloaded_gb:
            self.line_downloaded.set_data(timestamps, downloaded_gb)

            # 设置左Y轴（GB）
            self.ax_downloaded_gb.relim()
            self.ax_downloaded_gb.autoscale_view()
            self.ax_downloaded_gb.set_ylim(bottom=0)

            # ✅ 设置右Y轴（MB），使其与左轴成比例
            gb_min, gb_max = self.ax_downloaded_gb.get_ylim()
            self.ax_downloaded_mb.set_ylim(bottom=gb_min * 1024, top=gb_max * 1024)

            self.canvas_downloaded.draw()

        # 更新资源图表
        if timestamps and cpu:
            self.line_cpu.set_data(timestamps, cpu)
            self.line_memory.set_data(timestamps, memory)
            self.line_threads.set_data(timestamps, threads)
            self.ax_resources.relim()
            self.ax_resources.autoscale_view()
            self.canvas_resources.draw()

    def _format_speed(self, speed_bytes_per_second):
        """✅ 智能格式化速度显示（KB/s, MB/s, GB/s）"""
        if speed_bytes_per_second == 0:
            return "0 KB/s"

        if speed_bytes_per_second < 1024 * 1024:
            # 小于1MB/s，显示KB/s
            speed_kbps = speed_bytes_per_second / 1024
            return f"{speed_kbps:.2f} KB/s"
        elif speed_bytes_per_second < 1024 * 1024 * 1024:
            # 小于1GB/s，显示MB/s
            speed_mbps = speed_bytes_per_second / (1024 * 1024)
            return f"{speed_mbps:.2f} MB/s"
        else:
            # 大于等于1GB/s，显示GB/s
            speed_gbps = speed_bytes_per_second / (1024 ** 3)
            return f"{speed_gbps:.2f} GB/s"

    def _format_size(self, size_bytes):
        """✅ 智能格式化大小显示（MB, GB）"""
        if size_bytes == 0:
            return "0 MB"

        size_mb = size_bytes / (1024 * 1024)
        size_gb = size_bytes / (1024 ** 3)

        if size_gb >= 1:
            # 大于等于1GB，同时显示GB和MB
            return f"{size_gb:.2f} GB ({size_mb:.0f} MB)"
        else:
            # 小于1GB，显示MB
            return f"{size_mb:.2f} MB"

    def _update_stats_panel(self):
        """更新统计面板"""
        # 获取最新数据
        logs = self.db.get_recent_logs(minutes=1)

        if logs:
            latest = logs[-1]

            # ✅ 使用智能格式化的速度
            speed_text = self._format_speed(latest[2])
            self.speed_label.configure(
                text=f"当前速度: {speed_text}"
            )

            # ✅ 使用智能格式化的下载大小
            downloaded_text = self._format_size(latest[3])
            self.downloaded_label.configure(
                text=f"已下载: {downloaded_text}"
            )

            # 网络错误
            self.errors_label.configure(
                text=f"网络错误: {latest[7]}"
            )

        # 运行时间
        stats = self.db.get_statistics()
        if stats and stats['start_time']:
            elapsed = int(time.time() - stats['start_time'])
            hours = elapsed // 3600
            minutes = (elapsed % 3600) // 60
            seconds = elapsed % 60
            self.time_label.configure(
                text=f"运行时间: {hours:02d}:{minutes:02d}:{seconds:02d}"
            )

        # 更新统计文本
        self._update_stats_text()

    def _update_stats_text(self):
        """更新统计文本"""
        stats = self.db.get_statistics()

        if not stats:
            return

        text = "=" * 60 + "\n"
        text += "性能统计报告\n"
        text += "=" * 60 + "\n\n"

        # 基本统计
        text += "【基本统计】\n"
        text += f"监控时长: {stats.get('total_records', 0)} 个数据点\n"

        if stats['start_time']:
            start_dt = datetime.fromtimestamp(stats['start_time'])
            end_dt = datetime.fromtimestamp(stats['end_time'])
            duration = stats['end_time'] - stats['start_time']
            text += f"开始时间: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
            text += f"结束时间: {end_dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
            text += f"运行时长: {int(duration//3600):02d}小时{int((duration%3600)//60):02d}分\n"

        text += "\n【下载统计】\n"
        if stats['final_downloaded']:
            # ✅ 使用智能格式化
            text += f"总下载量: {self._format_size(stats['final_downloaded'])}\n"
        if stats['avg_speed']:
            text += f"平均速度: {self._format_speed(stats['avg_speed'])}\n"
        if stats['max_speed']:
            text += f"最高速度: {self._format_speed(stats['max_speed'])}\n"
        if stats['min_speed']:
            text += f"最低速度: {self._format_speed(stats['min_speed'])}\n"

        text += "\n" + "=" * 60 + "\n"
        text += "生成时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n"

        self.stats_text.delete("1.0", "end")
        self.stats_text.insert("1.0", text)

    def _load_historical_data(self):
        """加载历史数据"""
        self._update_charts()
        self._update_stats_text()

    def export_data(self):
        """导出数据"""
        from tkinter import filedialog, messagebox

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")],
            initialfile=f"era5_performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

        if not file_path:
            return

        try:
            logs = self.db.get_all_logs()

            with open(file_path, 'w', encoding='utf-8') as f:
                # ✅ 写入表头（添加多单位支持）
                f.write("时间,时间戳,下载速度(MB/s),下载速度(KB/s),累计下载(GB),累计下载(MB),活跃连接,CPU(%),内存(%),网络错误\n")

                # 写入数据
                for log in logs:
                    dt = log[1]
                    speed_mb_s = log[2] / (1024*1024) if log[2] > 0 else 0
                    speed_kb_s = log[2] / 1024 if log[2] > 0 else 0
                    downloaded_gb = log[3] / (1024**3) if log[3] > 0 else 0
                    downloaded_mb = log[3] / (1024*1024) if log[3] > 0 else 0

                    f.write(f"{dt},{log[0]:.2f},{speed_mb_s:.2f},{speed_kb_s:.2f},{downloaded_gb:.2f},{downloaded_mb:.2f},"
                           f"{log[4]},{log[5]:.1f},{log[6]:.1f},{log[7]}\n")

            messagebox.showinfo("成功", f"数据已导出到:\n{file_path}")

        except Exception as e:
            messagebox.showerror("错误", f"导出失败:\n{e}")


def main():
    """主函数"""
    app = PerformanceMonitorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
