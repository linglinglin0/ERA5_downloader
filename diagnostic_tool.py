#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ERA5下载软件 - 诊断监控工具
非侵入式实时监控，验证性能问题
"""

import psutil
import time
import threading
import os
import json
from datetime import datetime
from collections import deque
import socket

class DiagnosticMonitor:
    """诊断监控器"""

    def __init__(self, target_process_name="python", interval=5):
        self.interval = interval
        self.target_process_name = target_process_name
        self.running = False
        self.monitor_thread = None

        # 数据存储
        self.metrics = {
            'timestamps': deque(maxlen=720),  # 1小时数据（5秒间隔）
            'download_speed': deque(maxlen=720),
            'active_connections': deque(maxlen=720),
            'established_connections': deque(maxlen=720),
            'memory_mb': deque(maxlen=720),
            'memory_percent': deque(maxlen=720),
            'cpu_percent': deque(maxlen=720),
            'open_files': deque(maxlen=720),
            'thread_count': deque(maxlen=720),
            'error_rate': deque(maxlen=720),
            'retry_count': deque(maxlen=720),
        }

        # 统计数据
        self.total_errors = 0
        self.total_retries = 0
        self.connection_leaks = 0

    def find_target_process(self):
        """查找目标Python进程"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                # 查找运行ERA5下载程序的Python进程
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = proc.info['cmdline']
                    if cmdline and any('ERA5' in str(cmd) for cmd in cmdline):
                        return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def count_established_connections(self, process):
        """统计ESTABLISHED状态的连接数"""
        try:
            connections = process.connections(kind='inet')
            established = len([c for c in connections if c.status == 'ESTABLISHED'])
            total = len(connections)
            return established, total
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return 0, 0

    def analyze_network_errors(self):
        """分析网络错误日志"""
        error_log = "download_errors.log"
        if not os.path.exists(error_log):
            return 0, 0

        try:
            with open(error_log, 'r', encoding='utf-8') as f:
                content = f.read()

            # 统计错误类型
            error_types = {
                'ConnectionError': 0,
                'TimeoutError': 0,
                'ClientError': 0,
                'EndpointConnectionError': 0
            }

            for error_type in error_types:
                error_types[error_type] = content.count(error_type)

            total_errors = sum(error_types.values())

            # 统计重试次数（通过查找"重试"关键词）
            retry_count = content.count('重试')

            return total_errors, retry_count
        except Exception as e:
            print(f"[警告] 无法读取错误日志: {e}")
            return 0, 0

    def detect_connection_leak(self, process):
        """检测连接泄漏"""
        try:
            connections = process.connections(kind='inet')

            # 检测长时间处于非ESTABLISHED状态的连接
            suspicious = 0
            for conn in connections:
                if conn.status not in ['ESTABLISHED', 'CLOSE_WAIT']:
                    suspicious += 1

            return suspicious
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return 0

    def get_download_speed(self):
        """从进度文件估算下载速度"""
        try:
            # 查找最新的进度文件
            progress_files = []
            for root, dirs, files in os.walk('.'):
                for file in files:
                    if file == '.era5_download_progress.json':
                        progress_files.append(os.path.join(root, file))

            if not progress_files:
                return 0.0

            # 读取最新的进度文件
            latest_file = max(progress_files, key=os.path.getmtime)
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            completed_count = len(data.get('completed', []))

            # 简单估算：假设每个文件约1.2GB，除以时间间隔
            # 这里返回完成文件数作为速度指标
            return completed_count
        except Exception:
            return 0.0

    def collect_metrics(self, process):
        """收集所有指标"""
        try:
            now = datetime.now()
            timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

            # 基本指标
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = process.memory_percent()
            cpu_percent = process.cpu_percent(interval=0.1)

            # 连接相关
            established, total_conns = self.count_established_connections(process)
            connection_leaks = self.detect_connection_leak(process)

            # 其他指标
            try:
                open_files = process.num_fds() if hasattr(process, 'num_fds') else len(process.open_files())
            except:
                open_files = 0

            try:
                thread_count = process.num_threads()
            except:
                thread_count = 0

            # 网络错误
            total_errors, retry_count = self.analyze_network_errors()

            # 计算错误率
            error_rate = 0.0
            if self.metrics['error_rate']:
                prev_errors = self.total_errors
                if total_errors > prev_errors:
                    new_errors = total_errors - prev_errors
                    error_rate = new_errors / self.interval  # 每秒错误数

            self.total_errors = total_errors
            self.total_retries = retry_count

            # 下载速度（用完成文件数代替）
            completed_files = self.get_download_speed()

            # 存储数据
            self.metrics['timestamps'].append(timestamp)
            self.metrics['download_speed'].append(completed_files)
            self.metrics['active_connections'].append(total_conns)
            self.metrics['established_connections'].append(established)
            self.metrics['memory_mb'].append(memory_mb)
            self.metrics['memory_percent'].append(memory_percent)
            self.metrics['cpu_percent'].append(cpu_percent)
            self.metrics['open_files'].append(open_files)
            self.metrics['thread_count'].append(thread_count)
            self.metrics['error_rate'].append(error_rate)
            self.metrics['retry_count'].append(retry_count)

            return {
                'timestamp': timestamp,
                'memory_mb': memory_mb,
                'memory_percent': memory_percent,
                'cpu_percent': cpu_percent,
                'established': established,
                'total_conns': total_conns,
                'connection_leaks': connection_leaks,
                'open_files': open_files,
                'thread_count': thread_count,
                'total_errors': total_errors,
                'retry_count': retry_count,
                'completed_files': completed_files,
                'error_rate': error_rate
            }

        except psutil.NoSuchProcess:
            print("\n[错误] 目标进程已终止")
            self.running = False
            return None
        except Exception as e:
            print(f"\n[警告] 收集指标时出错: {e}")
            return None

    def display_dashboard(self, metrics):
        """显示监控面板"""
        if not metrics:
            return

        # 清屏（Windows兼容）
        os.system('cls' if os.name == 'nt' else 'clear')

        print("=" * 80)
        print(" " * 20 + "ERA5下载软件 - 实时诊断监控")
        print("=" * 80)
        print()

        # 时间信息
        print(f"📅 当前时间: {metrics['timestamp']}")
        print(f"⏱  监控时长: {len(self.metrics['timestamps']) * self.interval} 秒")
        print()

        # 速度和进度
        print("📊 下载状态")
        print("-" * 80)
        print(f"  已完成文件数: {metrics['completed_files']}")

        if len(self.metrics['download_speed']) > 1:
            speed = (self.metrics['download_speed'][-1] - self.metrics['download_speed'][-2]) / self.interval
            print(f"  当前速度: {speed:.2f} 文件/秒")

        print()

        # 连接状态（重点）
        print("🌐 网络连接状态（⚠️ 重点监控）")
        print("-" * 80)
        print(f"  ESTABLISHED连接: {metrics['established']}")
        print(f"  总连接数: {metrics['total_conns']}")
        print(f"  疑似泄漏连接: {metrics['connection_leaks']} ⚠️")

        # 趋势分析
        if len(self.metrics['established_connections']) >= 12:  # 1分钟数据
            recent = list(self.metrics['established_connections'])[-12:]
            trend = "上升 📈" if recent[-1] > recent[0] * 1.2 else "稳定 ➡️"
            print(f"  连接趋势: {trend} ({recent[0]} → {recent[-1]})")

            # 检测异常
            if metrics['connection_leaks'] > 10:
                print(f"  ⚠️ 警告: 检测到大量非活跃连接，可能存在连接泄漏！")
            elif metrics['total_conns'] > 50:
                print(f"  ⚠️ 警告: 连接数异常高，建议增加连接池大小！")

        print()

        # 错误统计
        print("❌ 错误与重试")
        print("-" * 80)
        print(f"  累计错误: {metrics['total_errors']}")
        print(f"  累计重试: {metrics['retry_count']}")
        print(f"  当前错误率: {metrics['error_rate']:.2f} 错误/秒")

        if metrics['total_errors'] > 0:
            # 计算重试效率
            retry_efficiency = (metrics['total_errors'] - metrics['retry_count']) / metrics['total_errors'] * 100
            print(f"  重试效率: {retry_efficiency:.1f}%")

        print()

        # 资源使用
        print("💻 系统资源")
        print("-" * 80)
        print(f"  内存使用: {metrics['memory_mb']:.1f} MB ({metrics['memory_percent']:.1f}%)")
        print(f"  CPU使用: {metrics['cpu_percent']:.1f}%")
        print(f"  线程数: {metrics['thread_count']}")
        print(f"  打开文件数: {metrics['open_files']}")

        # 内存趋势
        if len(self.metrics['memory_mb']) >= 12:
            recent = list(self.metrics['memory_mb'])[-12:]
            mem_growth = recent[-1] - recent[0]
            if mem_growth > 50:  # 1分钟内增长超过50MB
                print(f"  ⚠️ 警告: 内存增长过快 (+{mem_growth:.1f} MB/分钟)")

        print()

        # 健康检查
        print("🏥 系统健康诊断")
        print("-" * 80)

        health_issues = []

        # 检查连接泄漏
        if metrics['connection_leaks'] > 10:
            health_issues.append("❌ 严重连接泄漏")
        elif metrics['connection_leaks'] > 5:
            health_issues.append("⚠️ 轻微连接泄漏")

        # 检查内存增长
        if len(self.metrics['memory_mb']) >= 60:  # 5分钟数据
            mem_growth_5min = list(self.metrics['memory_mb'])[-1] - list(self.metrics['memory_mb'])[-60]
            if mem_growth_5min > 200:
                health_issues.append("❌ 内存泄漏严重")
            elif mem_growth_5min > 100:
                health_issues.append("⚠️ 内存持续增长")

        # 检查错误率
        if metrics['error_rate'] > 0.1:
            health_issues.append("❌ 高错误率")
        elif metrics['error_rate'] > 0.05:
            health_issues.append("⚠️ 错误率偏高")

        # 检查连接数
        if metrics['total_conns'] > 50:
            health_issues.append("⚠️ 连接数过多")

        if health_issues:
            for issue in health_issues:
                print(f"  {issue}")
        else:
            print("  ✅ 系统运行正常")

        print()
        print("=" * 80)
        print("按 Ctrl+C 停止监控")
        print("=" * 80)

    def generate_report(self):
        """生成诊断报告"""
        if not self.metrics['timestamps']:
            print("\n没有足够的数据生成报告")
            return

        print("\n" + "=" * 80)
        print(" " * 25 + "诊断报告")
        print("=" * 80)
        print()

        # 监控时长
        duration = len(self.metrics['timestamps']) * self.interval
        print(f"监控时长: {duration} 秒 ({duration/60:.1f} 分钟)")
        print()

        # 连接分析
        print("【连接分析】")
        established = list(self.metrics['established_connections'])
        if established:
            print(f"  平均ESTABLISHED连接: {sum(established)/len(established):.1f}")
            print(f"  峰值连接: {max(established)}")
            print(f"  最低连接: {min(established)}")

            # 趋势分析
            if len(established) >= 12:
                start_avg = sum(established[:12]) / 12
                end_avg = sum(established[-12:]) / 12
                if end_avg > start_avg * 1.5:
                    print(f"  ⚠️ 连接数呈上升趋势 ({start_avg:.1f} → {end_avg:.1f})")
                    print(f"  💡 建议: 检查HTTP响应是否正确关闭")

        print()

        # 内存分析
        print("【内存分析】")
        memory = list(self.metrics['memory_mb'])
        if memory:
            print(f"  初始内存: {memory[0]:.1f} MB")
            print(f"  峰值内存: {max(memory):.1f} MB")
            print(f"  当前内存: {memory[-1]:.1f} MB")
            print(f"  内存增长: {memory[-1] - memory[0]:.1f} MB")

            if len(memory) >= 60:
                growth_5min = memory[-1] - memory[-60]
                print(f"  5分钟增长: {growth_5min:.1f} MB")

                if growth_5min > 100:
                    print(f"  ⚠️ 内存增长过快，可能存在内存泄漏")
                    print(f"  💡 建议: 检查大对象的引用是否被释放")

        print()

        # 错误分析
        print("【错误分析】")
        if self.total_errors > 0:
            print(f"  总错误次数: {self.total_errors}")
            print(f"  总重试次数: {self.total_retries}")

            if duration > 0:
                error_per_min = self.total_errors / (duration / 60)
                print(f"  平均错误率: {error_per_min:.2f} 次/分钟")

                # 重试开销
                retry_time = self.total_retries * 10  # 假设每次重试浪费10秒
                print(f"  重试浪费时间: {retry_time/60:.1f} 分钟")

            if self.total_errors > 10:
                print(f"  ⚠️ 错误次数过多，请检查:")
                print(f"     - 网络连接质量")
                print(f"     - 连接池配置")
                print(f"     - 超时设置")
        else:
            print("  ✅ 未检测到错误")

        print()
        print("=" * 80)

    def start(self):
        """开始监控"""
        print("正在查找ERA5下载程序进程...")

        process = self.find_target_process()
        if not process:
            print("未找到运行中的ERA5下载程序")
            print("请先启动下载程序，然后再运行此监控工具")
            return

        print(f"找到目标进程 PID={process.pid}")
        print(f"开始监控，间隔 {self.interval} 秒...")
        print()

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(process,), daemon=True)
        self.monitor_thread.start()

        try:
            # 主线程等待
            while self.monitor_thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n收到停止信号...")
            self.running = False
            self.monitor_thread.join(timeout=5)

        # 生成报告
        self.generate_report()

    def _monitor_loop(self, process):
        """监控循环"""
        while self.running:
            try:
                metrics = self.collect_metrics(process)
                if metrics:
                    self.display_dashboard(metrics)
            except psutil.NoSuchProcess:
                print("\n目标进程已终止")
                break
            except Exception as e:
                print(f"\n监控出错: {e}")

            time.sleep(self.interval)


def main():
    """主函数"""
    print("=" * 80)
    print(" " * 15 + "ERA5下载软件 - 诊断监控工具")
    print("=" * 80)
    print()
    print("功能说明:")
    print("  - 实时监控网络连接状态（检测连接泄漏）")
    print("  - 监控内存使用趋势（检测内存泄漏）")
    print("  - 统计网络错误和重试次数")
    print("  - 分析性能问题并提供优化建议")
    print()
    print("使用方法:")
    print("  1. 先启动 ERA5下载软件")
    print("  2. 运行本监控工具")
    print("  3. 让下载运行一段时间（建议至少30分钟）")
    print("  4. 按 Ctrl+C 停止监控并查看报告")
    print()
    print("提示: 观察以下指标的变化趋势:")
    print("  - ESTABLISHED连接数: 持续增长 = 连接泄漏")
    print("  - 内存使用: 持续增长 = 内存泄漏")
    print("  - 错误率: 随时间增长 = 连接池耗尽")
    print()

    monitor = DiagnosticMonitor(interval=5)  # 5秒刷新一次
    monitor.start()


if __name__ == "__main__":
    main()
