#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ERA5下载器 - 高级特性补丁
包含：
1. 自适应速率限制器
2. 连接池定期重建
3. 健康检查和自动恢复
4. 性能监控和日志
"""

import time
import threading
from collections import deque
from dataclasses import dataclass
from typing import Optional
import traceback

# ================= 自适应速率限制器 =================

class AdaptiveRateLimiter:
    """
    自适应速率限制器

    原理：
    1. 监控请求成功率和延迟
    2. 成功率低时自动降低请求速率
    3. 成功率高时逐渐提高请求速率

    使用场景：
    - 应对AWS S3请求速率限制
    - 避免触发429/503错误
    - 优化长期下载稳定性
    """

    def __init__(self, initial_delay=0.1, max_delay=5.0, min_delay=0.0):
        self.current_delay = initial_delay
        self.max_delay = max_delay
        self.min_delay = min_delay

        # 统计数据
        self.request_times = deque(maxlen=200)  # 保存最近200个请求
        self.lock = threading.Lock()

        # 配置
        self.target_success_rate = 0.95  # 目标成功率
        self.adjustment_step = 0.05      # 每次调整步长

    def acquire(self):
        """获取请求许可（可能阻塞）"""
        delay = self.get_current_delay()
        if delay > 0:
            time.sleep(delay)

    def record_request(self, success: bool, latency: float):
        """
        记录请求结果

        Args:
            success: 请求是否成功
            latency: 请求延迟（秒）
        """
        with self.lock:
            now = time.time()
            self.request_times.append({
                'time': now,
                'success': success,
                'latency': latency
            })

            # 每10个请求调整一次
            if len(self.request_times) >= 10:
                self._adjust_rate()

    def get_current_delay(self) -> float:
        """获取当前延迟"""
        with self.lock:
            return self.current_delay

    def get_success_rate(self, window_seconds=60) -> float:
        """
        计算最近的成功率

        Args:
            window_seconds: 时间窗口（秒）

        Returns:
            成功率 (0.0 - 1.0)
        """
        with self.lock:
            if not self.request_times:
                return 1.0

            now = time.time()
            cutoff = now - window_seconds

            # 筛选时间窗口内的请求
            recent = [
                r for r in self.request_times
                if r['time'] >= cutoff
            ]

            if not recent:
                return 1.0

            success_count = sum(1 for r in recent if r['success'])
            return success_count / len(recent)

    def get_average_latency(self, window_seconds=60) -> float:
        """
        计算最近的平均延迟

        Returns:
            平均延迟（秒）
        """
        with self.lock:
            if not self.request_times:
                return 0.0

            now = time.time()
            cutoff = now - window_seconds

            recent = [
                r for r in self.request_times
                if r['time'] >= cutoff and r['success']
            ]

            if not recent:
                return 0.0

            return sum(r['latency'] for r in recent) / len(recent)

    def _adjust_rate(self):
        """根据成功率调整速率"""
        success_rate = self.get_success_rate()
        avg_latency = self.get_average_latency()

        # 成功率过低，增加延迟
        if success_rate < self.target_success_rate:
            old_delay = self.current_delay
            self.current_delay = min(
                self.max_delay,
                self.current_delay + self.adjustment_step
            )

            if self.current_delay != old_delay:
                print(f"[RateLimiter] 成功率下降 ({success_rate:.1%}), 增加延迟到 {self.current_delay:.2f}s")

        # 成功率高，减少延迟
        elif success_rate > 0.98 and self.current_delay > self.min_delay:
            old_delay = self.current_delay
            self.current_delay = max(
                self.min_delay,
                self.current_delay - self.adjustment_step
            )

            if self.current_delay != old_delay:
                print(f"[RateLimiter] 成功率良好 ({success_rate:.1%}), 减少延迟到 {self.current_delay:.2f}s")

    def get_stats(self) -> dict:
        """获取统计信息"""
        with self.lock:
            if not self.request_times:
                return {}

            return {
                'current_delay': self.current_delay,
                'success_rate': self.get_success_rate(),
                'avg_latency': self.get_average_latency(),
                'total_requests': len(self.request_times)
            }


# ================= 连接池管理器 =================

class ConnectionPoolManager:
    """
    连接池管理器

    功能：
    1. 定期重建连接池
    2. 健康检查
    3. 自动恢复
    """

    def __init__(self, rebuild_interval=3600, health_check_interval=300):
        """
        Args:
            rebuild_interval: 重建间隔（秒），默认1小时
            health_check_interval: 健康检查间隔（秒），默认5分钟
        """
        self.rebuild_interval = rebuild_interval
        self.health_check_interval = health_check_interval

        self.last_rebuild_time = 0
        self.last_health_check = 0
        self.s3_client = None
        self.bucket_name = None

        # 健康状态
        self.health_score = 1.0  # 0.0 - 1.0
        self.consecutive_failures = 0

    def set_client(self, s3_client, bucket_name):
        """设置S3客户端"""
        self.s3_client = s3_client
        self.bucket_name = bucket_name
        self.last_rebuild_time = time.time()

    def check_and_maintain(self, log_callback=None):
        """
        检查并维护连接池

        Args:
            log_callback: 日志回调函数

        Returns:
            bool: 是否进行了重建
        """
        now = time.time()

        # 检查是否需要健康检查
        if now - self.last_health_check > self.health_check_interval:
            self.last_health_check = now

            is_healthy = self._health_check()

            if not is_healthy:
                if log_callback:
                    log_callback("连接不健康，准备重建...", "orange")

                self._rebuild_pool()

                if log_callback:
                    log_callback("连接池已重建", "#00e676")

                return True

        # 定期重建
        if now - self.last_rebuild_time > self.rebuild_interval:
            if log_callback:
                log_callback(f"已运行{int((now-self.last_rebuild_time)/60)}分钟，定期重建连接池...", "orange")

            self._rebuild_pool()

            if log_callback:
                log_callback("连接池已重建", "#00e676")

            return True

        return False

    def _health_check(self) -> bool:
        """
        健康检查

        Returns:
            bool: 是否健康
        """
        if not self.s3_client:
            return False

        try:
            # 尝试获取bucket元数据
            start = time.time()
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            latency = time.time() - start

            # 更新健康分数
            if latency < 1.0:
                self.health_score = min(1.0, self.health_score + 0.1)
            elif latency < 3.0:
                self.health_score = max(0.5, self.health_score)
            else:
                self.health_score = max(0.0, self.health_score - 0.2)

            # 检查是否健康
            if latency > 10.0:
                self.consecutive_failures += 1
                return False

            self.consecutive_failures = 0
            return self.health_score > 0.3

        except Exception as e:
            self.consecutive_failures += 1
            self.health_score = max(0.0, self.health_score - 0.3)
            print(f"[HealthCheck] 失败: {e}")
            return False

    def _rebuild_pool(self):
        """重建连接池"""
        if not self.s3_client:
            return

        try:
            # 关闭旧连接
            self.s3_client._endpoint.http_session.close()

            # 重新创建连接（需要外部重新创建S3客户端）
            self.last_rebuild_time = time.time()
            self.health_score = 1.0
            self.consecutive_failures = 0

        except Exception as e:
            print(f"[RebuildPool] 重建失败: {e}")

    def get_health_status(self) -> dict:
        """获取健康状态"""
        return {
            'health_score': self.health_score,
            'consecutive_failures': self.consecutive_failures,
            'time_since_rebuild': time.time() - self.last_rebuild_time,
            'time_since_check': time.time() - self.last_health_check
        }


# ================= 性能监控器 =================

class PerformanceMonitor:
    """
    性能监控器

    功能：
    1. 记录下载速度
    2. 检测速度衰减
    3. 生成性能报告
    """

    def __init__(self, window_size=600):
        """
        Args:
            window_size: 监控窗口大小（秒）
        """
        self.window_size = window_size
        self.snapshots = deque(maxlen=1000)  # 保存最近1000个快照
        self.lock = threading.Lock()

    def record_snapshot(self, downloaded_bytes: int, elapsed_time: float):
        """
        记录性能快照

        Args:
            downloaded_bytes: 已下载字节数
            elapsed_time: 已用时间（秒）
        """
        with self.lock:
            now = time.time()
            speed_mbps = (downloaded_bytes / elapsed_time) / (1024 * 1024) if elapsed_time > 0 else 0

            self.snapshots.append({
                'time': now,
                'speed_mbps': speed_mbps,
                'downloaded_mb': downloaded_bytes / (1024 * 1024)
            })

    def get_current_speed(self) -> float:
        """获取当前速度（MB/s）"""
        with self.lock:
            if not self.snapshots:
                return 0.0

            return self.snapshots[-1]['speed_mbps']

    def get_average_speed(self, window_seconds=60) -> float:
        """
        获取平均速度

        Args:
            window_seconds: 时间窗口（秒）

        Returns:
            平均速度（MB/s）
        """
        with self.lock:
            if not self.snapshots:
                return 0.0

            now = time.time()
            cutoff = now - window_seconds

            recent = [
                s for s in self.snapshots
                if s['time'] >= cutoff
            ]

            if not recent:
                return 0.0

            return sum(s['speed_mbps'] for s in recent) / len(recent)

    def detect_decay(self, compare_window=300) -> dict:
        """
        检测速度衰减

        Args:
            compare_window: 对比窗口（秒），默认5分钟

        Returns:
            dict: 衰减信息
        """
        with self.lock:
            if len(self.snapshots) < 20:
                return {'detected': False, 'reason': '数据不足'}

            now = time.time()

            # 最近窗口
            recent = [
                s for s in self.snapshots
                if s['time'] >= now - compare_window
            ]

            # 之前窗口
            old = [
                s for s in self.snapshots
                if now - compare_window * 2 <= s['time'] < now - compare_window
            ]

            if not recent or not old:
                return {'detected': False, 'reason': '数据不足'}

            recent_avg = sum(s['speed_mbps'] for s in recent) / len(recent)
            old_avg = sum(s['speed_mbps'] for s in old) / len(old)

            if old_avg == 0:
                return {'detected': False, 'reason': '基准速度为0'}

            decay_rate = ((old_avg - recent_avg) / old_avg) * 100

            # 判断是否存在严重衰减
            detected = decay_rate > 30

            return {
                'detected': detected,
                'decay_rate': decay_rate,
                'old_speed': old_avg,
                'current_speed': recent_avg,
                'severity': 'high' if decay_rate > 50 else ('medium' if decay_rate > 30 else 'low')
            }

    def generate_report(self) -> str:
        """生成性能报告"""
        with self.lock:
            if not self.snapshots:
                return "无性能数据"

            duration = self.snapshots[-1]['time'] - self.snapshots[0]['time']
            total_mb = self.snapshots[-1]['downloaded_mb']
            avg_speed = total_mb / (duration / 60) if duration > 0 else 0  # MB/min

            current_speed = self.get_current_speed()
            decay_info = self.detect_decay()

            report = []
            report.append("=" * 60)
            report.append("性能监控报告")
            report.append("=" * 60)
            report.append(f"运行时长: {int(duration/60)}分{int(duration%60)}秒")
            report.append(f"已下载: {total_mb:.1f} MB")
            report.append(f"平均速度: {avg_speed:.1f} MB/min")
            report.append(f"当前速度: {current_speed:.2f} MB/s")

            if decay_info['detected']:
                report.append("")
                report.append("[警告] 检测到速度衰减!")
                report.append(f"衰减率: {decay_info['decay_rate']:.1f}%")
                report.append(f"之前速度: {decay_info['old_speed']:.2f} MB/s")
                report.append(f"当前速度: {decay_info['current_speed']:.2f} MB/s")
                report.append(f"严重程度: {decay_info['severity']}")

            report.append("=" * 60)

            return "\n".join(report)


# ================= 使用示例 =================

if __name__ == "__main__":
    print("高级特性模块 - 使用示例")
    print()
    print("这是一个补丁模块，需要集成到主程序中。")
    print()
    print("包含的功能：")
    print("1. AdaptiveRateLimiter - 自适应速率限制")
    print("2. ConnectionPoolManager - 连接池管理")
    print("3. PerformanceMonitor - 性能监控")
    print()
    print("集成方法：")
    print("```python")
    print("from era5_advanced_features import (")
    print("    AdaptiveRateLimiter,")
    print("    ConnectionPoolManager,")
    print("    PerformanceMonitor")
    print(")")
    print()
    print("# 初始化")
    print("rate_limiter = AdaptiveRateLimiter()")
    print("pool_manager = ConnectionPoolManager()")
    print("perf_monitor = PerformanceMonitor()")
    print()
    print("# 在下载循环中使用")
    print("rate_limiter.acquire()")
    print("response = s3_client.get_object(...)")
    print("rate_limiter.record_request(success=True, latency=0.5)")
    print()
    print("# 定期维护")
    print("pool_manager.check_and_maintain(log_callback)")
    print("perf_monitor.record_snapshot(bytes, elapsed)")
    print("```")
