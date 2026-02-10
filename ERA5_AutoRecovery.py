#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ERA5下载器 v3.1 - 智能自动恢复版

新增功能：
1. 实时监控下载速度
2. 检测速度持续下降
3. 自动重启下载软件
4. 断点续传无缝恢复
5. 智能阈值判断

基于 v3.0 版本增强
"""

import os
import sys
import time
import json
import ctypes
import threading
import subprocess
from datetime import datetime
from pathlib import Path

# Windows API导入（延迟导入，避免在非Windows系统出错）
try:
    import win32gui
    import win32api
    import win32con
    import win32event
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("[警告] pywin32未安装，部分Windows功能将不可用")

# 检测是否在运行中
def is_already_running():
    """检查是否已有实例在运行"""
    try:
        # Windows系统使用mutex
        import win32event
        import win32api
        import winerror

        mutex_name = "Global\\ERA5_Downloader_v31"
        try:
            mutex = win32event.CreateMutex(None, False, mutex_name)
            if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
                return True
        except:
            pass
    except ImportError:
        # 如果pywin32未安装，使用文件锁
        lock_file = Path(".era5_lock")
        if lock_file.exists():
            try:
                lock_file.unlink()
                return False
            except:
                return True

    return False

class SpeedMonitor:
    """速度监控器"""

    def __init__(self, low_speed_threshold=500*1024,  # 500 KB/s
                 duration_threshold=30,           # 持续30秒
                 check_interval=5):               # 每5秒检查一次
        self.low_speed_threshold = low_speed_threshold
        self.duration_threshold = duration_threshold
        self.check_interval = check_interval

        self.low_speed_samples = 0  # 低速样本计数
        self.speed_history = []     # 速度历史

        self.running = False
        self.restart_callback = None

    def get_current_speed(self):
        """获取当前下载速度（从性能监控器数据库读取）"""
        try:
            import sqlite3

            db_path = "era5_performance.db"
            if not os.path.exists(db_path):
                return 0

            # 读取最近5秒的记录
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cutoff_time = time.time() - 5
            cursor.execute('''
                SELECT download_speed
                FROM performance_logs
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 5
            ''', (cutoff_time,))

            speeds = [row[0] for row in cursor.fetchall()]
            conn.close()

            if speeds:
                # 返回平均值（bytes/s）
                return sum(speeds) / len(speeds)
            return 0

        except Exception as e:
            print(f"[SpeedMonitor] 获取速度失败: {e}")
            return 0

    def check_speed_condition(self):
        """检查速度条件"""
        current_speed = self.get_current_speed()

        # 添加到历史
        self.speed_history.append({
            'time': time.time(),
            'speed': current_speed
        })

        # 只保留最近1分钟的历史
        cutoff = time.time() - 60
        self.speed_history = [s for s in self.speed_history if s['time'] >= cutoff]

        # 检查是否低速
        if current_speed < self.low_speed_threshold:
            self.low_speed_samples += 1
            print(f"[SpeedMonitor] 检测到低速: {current_speed / 1024:.1f} KB/s "
                  f"(样本: {self.low_speed_samples}/{self.duration_threshold // self.check_interval})")
        else:
            # 速度正常，重置计数
            if self.low_speed_samples > 0:
                print(f"[SpeedMonitor] 速度恢复: {current_speed / 1024:.1f} KB/s, "
                      f"重置低速计数")
            self.low_speed_samples = 0

        # 检查是否达到重启阈值
        if self.low_speed_samples >= (self.duration_threshold // self.check_interval):
            return True, current_speed
        return False, current_speed

    def start_monitoring(self, restart_callback):
        """开始监控"""
        self.running = True
        self.restart_callback = restart_callback

        print(f"[SpeedMonitor] 启动速度监控")
        print(f"[SpeedMonitor] 低速阈值: {self.low_speed_threshold / 1024:.0f} KB/s")
        print(f"[SpeedMonitor] 持续时间: {self.duration_threshold}秒")
        print(f"[SpeedMonitor] 检查间隔: {self.check_interval}秒")
        print("-" * 60)

        while self.running:
            should_restart, speed = self.check_speed_condition()

            if should_restart:
                print(f"[SpeedMonitor] ⚠️ 触发自动重启条件！")
                print(f"[SpeedMonitor] 当前速度: {speed / 1024:.1f} KB/s")
                print(f"[SpeedMonitor] 低速持续时间: {self.duration_threshold}秒")
                print("=" * 60)

                # 执行重启
                self.restart_and_resume()

                # 重置计数
                self.low_speed_samples = 0

                # 等待30秒后继续监控
                print("[SpeedMonitor] 等待30秒后继续监控...")
                time.sleep(30)
            else:
                time.sleep(self.check_interval)

    def restart_and_resume(self):
        """重启下载器并恢复"""
        if not self.restart_callback:
            print("[SpeedMonitor] 错误: 未设置重启回调")
            return

        try:
            # 调用重启回调
            self.restart_callback()

        except Exception as e:
            print(f"[SpeedMonitor] 重启失败: {e}")
            import traceback
            traceback.print_exc()

    def stop(self):
        """停止监控"""
        self.running = False


class AutoRecoveryDownloader:
    """带自动恢复功能的下载器"""

    def __init__(self):
        self.downloader_process = None
        self.config = {}
        self.config_file = ".era5_auto_recovery_config.json"

    def load_config(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                print(f"[AutoRecovery] 配置已加载")
            except Exception as e:
                print(f"[AutoRecovery] 加载配置失败: {e}")

    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AutoRecovery] 保存配置失败: {e}")

    def start_downloader(self):
        """启动下载器"""
        if self.downloader_process:
            # 先停止现有进程
            self.stop_downloader()

        try:
            # 使用v3.0版本
            script_path = "ERA5download_GUI_v3.py"

            if not os.path.exists(script_path):
                print(f"[AutoRecovery] 错误: 找不到 {script_path}")
                return False

            # 启动进程
            self.downloader_process = subprocess.Popen(
                [sys.executable, script_path],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            print(f"[AutoRecovery] 下载器已启动 (PID: {self.downloader_process.pid})")
            return True

        except Exception as e:
            print(f"[AutoRecovery] 启动失败: {e}")
            return False

    def stop_downloader(self):
        """停止下载器"""
        if self.downloader_process:
            try:
                # 发送关闭消息（Windows）
                if WIN32_AVAILABLE:
                    # 查找窗口（尝试多种可能的标题）
                    hwnd = None
                    for title in ["ERA5 下载器 v3.0", "ERA5 下载器", "ERA5 Download Manager"]:
                        hwnd = win32gui.FindWindow("CTkTk", title)
                        if hwnd:
                            break

                    if hwnd:
                        # 发送关闭消息
                        win32api.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                        print(f"[AutoRecovery] 已发送关闭信号")
                    else:
                        print(f"[AutoRecovery] 未找到下载器窗口，将直接终止进程")
                else:
                    print(f"[AutoRecovery] Windows API不可用，将直接终止进程")

                # 等待进程结束（最多10秒）
                try:
                    self.downloader_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # 超时后强制终止
                    if self.downloader_process.poll() is None:
                        print(f"[AutoRecovery] 强制终止进程")
                        self.downloader_process.terminate()

                self.downloader_process = None
                print(f"[AutoRecovery] 下载器已停止")

            except Exception as e:
                print(f"[AutoRecovery] 停止失败: {e}")
                import traceback
                traceback.print_exc()

    def restart_downloader(self):
        """重启下载器"""
        print(f"[AutoRecovery] ========== 开始自动重启 ==========")
        print(f"[AutoRecovery] 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 停止当前下载器
        print(f"[AutoRecovery] 步骤1/3: 停止当前下载器...")
        self.stop_downloader()

        # 等待5秒，确保进程完全停止
        print(f"[AutoRecovery] 等待5秒...")
        time.sleep(5)

        # 重新启动
        print(f"[AutoRecovery] 步骤2/3: 重新启动下载器...")
        success = self.start_downloader()

        if success:
            # 等待初始化
            print(f"[AutoRecovery] 等待10秒初始化...")
            time.sleep(10)

            # 自动点击"开始下载"（如果配置了）
            if self.config.get('auto_start', False):
                print(f"[AutoRecovery] 步骤3/3: 自动开始下载...")
                self.auto_start_download()
            else:
                print(f"[AutoRecovery] 步骤3/3: 请手动点击'开始下载'按钮")

            print(f"[AutoRecovery] ========== 重启完成 =========")
        else:
            print(f"[AutoRecovery] ========== 重启失败 ==========")

    def auto_start_download(self):
        """自动开始下载（模拟点击）"""
        try:
            if not WIN32_AVAILABLE:
                print(f"[AutoRecovery] Windows API不可用，无法自动开始下载")
                return

            # 查找下载器窗口（尝试多种可能的标题）
            hwnd = None
            for title in ["ERA5 下载器 v3.0", "ERA5 下载器", "ERA5 Download Manager"]:
                hwnd = win32gui.FindWindow("CTkTk", title)
                if hwnd:
                    print(f"[AutoRecovery] 找到下载器窗口: {title}")
                    break

            if hwnd:
                # 获取配置信息
                date = self.config.get('date', '202510')
                print(f"[AutoRecovery] 配置日期: {date}")
                print(f"[AutoRecovery] 提示: 请确认配置正确并点击'开始下载'按钮")
                # TODO: 实现自动化点击逻辑（需要知道按钮的类名或ID）
            else:
                print(f"[AutoRecovery] 未找到下载器窗口，请手动点击'开始下载'")

        except Exception as e:
            print(f"[AutoRecovery] 自动开始失败: {e}")
            import traceback
            traceback.print_exc()


def main():
    """主函数"""
    print("=" * 70)
    print(" " * 18 + "ERA5下载器 v3.1 - 智能自动恢复版")
    print("=" * 70)
    print()

    # 检查是否已运行
    if is_already_running():
        print("[错误] 检测到程序已在运行！")
        print()
        input("按Enter键退出...")
        return

    print("[功能说明]")
    print("-" * 70)
    print("1. 启动 ERA5下载器 v3.0")
    print("2. 实时监控下载速度")
    print("3. 当速度持续 30秒低于 500 KB/s 时，自动重启下载器")
    print("4. 利用断点续传无缝恢复下载")
    print()
    print("[配置选项]")
    print("-" * 70)

    # 获取用户配置
    try:
        low_speed_kb = input("请输入低速阈值 (KB/s) [默认: 500]: ").strip()
        low_speed_threshold = int(low_speed_kb) * 1024 if low_speed_kb else 500 * 1024

        duration_sec = input("请输入持续时间 (秒) [默认: 30]: ").strip()
        duration_threshold = int(duration_sec) if duration_sec else 30

        auto_start = input("是否自动开始下载？(y/n) [默认: n]: ").strip().lower()
        auto_start = (auto_start == 'y')

    except ValueError:
        print("[错误] 输入无效，使用默认值")
        low_speed_threshold = 500 * 1024
        duration_threshold = 30
        auto_start = False

    print()
    print("[配置确认]")
    print(f"  低速阈值: {low_speed_threshold / 1024:.0f} KB/s")
    print(f"  持续时间: {duration_threshold} 秒")
    print(f"  自动开始: {'是' if auto_start else '否'}")
    print()

    input("按Enter键启动自动恢复系统...")
    print()

    # 创建自动恢复下载器
    auto_recovery = AutoRecoveryDownloader()
    auto_recovery.config['auto_start'] = auto_start
    auto_recovery.save_config()

    # 创建速度监控器
    speed_monitor = SpeedMonitor(
        low_speed_threshold=low_speed_threshold,
        duration_threshold=duration_threshold
    )

    # 启动下载器
    print("[AutoRecovery] 正在启动ERA5下载器 v3.0...")
    auto_recovery.start_downloader()

    # 等待用户手动配置和开始下载
    print()
    print("=" * 70)
    print("[提示] 请在下载器中配置以下参数后点击'开始下载':")
    print("  1. 日期 (如: 202510)")
    print("  2. 保存根目录")
    print("  3. 线程数 (建议 3-5)")
    print("  4. 选择变量")
    print("=" * 70)
    print()
    print("[监控器] 30秒后将开始监控下载速度...")
    print()

    # 等待30秒让用户启动
    time.sleep(30)

    # 定义重启回调
    def restart_callback():
        auto_recovery.restart_downloader()

    # 设置回调并启动监控
    speed_monitor.restart_callback = restart_callback

    try:
        speed_monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n[AutoRecovery] 用户中断")

    # 清理
    if auto_recovery.downloader_process:
        print()
        print("[AutoRecovery] 正在停止下载器...")
        auto_recovery.stop_downloader()


if __name__ == "__main__":
    main()
