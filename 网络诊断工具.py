#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""网络诊断工具 - 检测S3限流和网络问题"""

import socket
import time
import requests
import subprocess
import threading
from collections import deque

class NetworkDiagnostics:
    """网络诊断工具"""

    def __init__(self):
        self.s3_endpoint = "s3.amazonaws.com"
        self.bucket_name = "nsf-ncar-era5"
        self.results = {}

    def test_dns_resolution(self, iterations=10):
        """测试DNS解析性能"""
        print("=" * 80)
        print(" " * 25 + "DNS解析测试")
        print("=" * 80)
        print()

        latencies = []
        for i in range(iterations):
            start = time.time()
            try:
                ip = socket.gethostbyname(self.s3_endpoint)
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                print(f"[{i+1:2d}] {self.s3_endpoint} -> {ip}  ({latency:.2f} ms)")
            except Exception as e:
                print(f"[{i+1:2d}] DNS解析失败: {e}")

        if latencies:
            avg = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)

            print()
            print(f"平均延迟: {avg:.2f} ms")
            print(f"最大延迟: {max_latency:.2f} ms")
            print(f"最小延迟: {min_latency:.2f} ms")

            # 判断DNS健康度
            if avg < 50:
                status = "[OK] DNS解析速度快"
                color = "绿色"
            elif avg < 200:
                status = "[WARN] DNS解析较慢"
                color = "黄色"
            else:
                status = "[ERROR] DNS解析过慢"
                color = "红色"

            print(f"状态: {status}")

            self.results['dns'] = {
                'avg': avg,
                'max': max_latency,
                'min': min_latency,
                'status': status
            }
        print()

    def test_tcp_connection(self, host="s3.amazonaws.com", port=443, iterations=10):
        """测试TCP连接性能"""
        print("=" * 80)
        print(" " * 25 + "TCP连接测试")
        print("=" * 80)
        print()

        latencies = []
        failures = 0

        for i in range(iterations):
            start = time.time()
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((host, port))
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                sock.close()
                print(f"[{i+1:2d}] TCP连接成功 ({latency:.2f} ms)")
            except Exception as e:
                failures += 1
                print(f"[{i+1:2d}] TCP连接失败: {e}")

        print()
        if latencies:
            avg = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)

            print(f"成功连接: {len(latencies)}/{iterations}")
            print(f"平均延迟: {avg:.2f} ms")
            print(f"最大延迟: {max_latency:.2f} ms")
            print(f"最小延迟: {min_latency:.2f} ms")

            # 判断TCP健康度
            if avg < 100 and failures == 0:
                status = "[OK] TCP连接质量优秀"
            elif avg < 300:
                status = "[WARN] TCP连接质量一般"
            else:
                status = "[ERROR] TCP连接质量差"

            print(f"状态: {status}")

            self.results['tcp'] = {
                'avg': avg,
                'max': max_latency,
                'failures': failures,
                'status': status
            }
        print()

    def test_http_download(self, test_size=1024*1024):
        """测试HTTP下载速度"""
        print("=" * 80)
        print(" " * 25 + "HTTP下载速度测试")
        print("=" * 80)
        print()

        # 使用公开的测试文件
        test_url = f"https://{self.bucket_name}.s3.amazonaws.com/README.html"

        try:
            print(f"下载测试文件: {test_url}")
            start = time.time()

            response = requests.get(test_url, timeout=30, stream=True)
            total_size = 0

            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    total_size += len(chunk)
                    if total_size >= test_size:
                        break

            elapsed = time.time() - start
            speed_mbps = (total_size / elapsed) / (1024 * 1024)

            print(f"下载大小: {total_size / 1024:.2f} KB")
            print(f"耗时: {elapsed:.2f} 秒")
            print(f"平均速度: {speed_mbps:.2f} MB/s")

            # 判断速度
            if speed_mbps > 10:
                status = "[OK] 下载速度快"
            elif speed_mbps > 2:
                status = "[WARN] 下载速度一般"
            else:
                status = "[ERROR] 下载速度过慢"

            print(f"状态: {status}")

            self.results['http'] = {
                'speed_mbps': speed_mbps,
                'elapsed': elapsed,
                'status': status
            }

        except Exception as e:
            print(f"[ERROR] HTTP下载测试失败: {e}")
            self.results['http'] = {'error': str(e)}

        print()

    def check_active_connections(self):
        """检查活跃的S3连接"""
        print("=" * 80)
        print(" " * 25 + "活跃连接检查")
        print("=" * 80)
        print()

        try:
            # Windows使用netstat
            result = subprocess.run(
                ['netstat', '-an'],
                capture_output=True,
                text=True,
                timeout=10
            )

            lines = result.stdout.split('\n')

            established_count = 0
            close_wait_count = 0
            time_wait_count = 0

            s3_connections = []

            for line in lines:
                if '52.218' in line or 's3' in line.lower():
                    s3_connections.append(line)

                if 'ESTABLISHED' in line:
                    established_count += 1
                elif 'CLOSE_WAIT' in line:
                    close_wait_count += 1
                elif 'TIME_WAIT' in line:
                    time_wait_count += 1

            print(f"ESTABLISHED 连接数: {established_count}")
            print(f"CLOSE_WAIT 连接数: {close_wait_count}")
            print(f"TIME_WAIT 连接数: {time_wait_count}")
            print()

            if len(s3_connections) > 0:
                print(f"S3相关连接 ({len(s3_connections)} 个):")
                for conn in s3_connections[:10]:  # 只显示前10个
                    print(f"  {conn}")
                if len(s3_connections) > 10:
                    print(f"  ... 还有 {len(s3_connections)-10} 个连接")

            print()
            # 健康判断
            if close_wait_count > 10:
                status = "[ERROR] 发现大量CLOSE_WAIT，连接未正确关闭"
            elif established_count > 50:
                status = "[WARN] 活跃连接数过多"
            elif established_count > 20:
                status = "[WARN] 活跃连接数略多"
            else:
                status = "[OK] 连接数正常"

            print(f"状态: {status}")

            self.results['connections'] = {
                'established': established_count,
                'close_wait': close_wait_count,
                'time_wait': time_wait_count,
                's3_count': len(s3_connections),
                'status': status
            }

        except Exception as e:
            print(f"[ERROR] 检查连接失败: {e}")

        print()

    def continuous_speed_test(self, duration=60):
        """持续速度测试（检测衰减）"""
        print("=" * 80)
        print(f" " * 20 + f"持续速度测试 ({duration}秒)")
        print("=" * 80)
        print()
        print("正在下载小文件以测试速度衰减...")
        print()

        speeds = deque(maxlen=duration)
        start_time = time.time()

        while time.time() - start_time < duration:
            try:
                test_start = time.time()
                response = requests.get(
                    f"https://{self.bucket_name}.s3.amazonaws.com/README.html",
                    timeout=10,
                    stream=True
                )

                size = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        size += len(chunk)
                        if size >= 100*1024:  # 100KB
                            break

                elapsed = time.time() - test_start
                speed = (size / elapsed) / (1024 * 1024)  # MB/s
                speeds.append(speed)

                # 每5秒输出一次
                if len(speeds) % 5 == 0:
                    elapsed_time = int(time.time() - start_time)
                    recent_avg = sum(list(speeds)[-5:]) / 5
                    print(f"[{elapsed_time:3d}s] 当前速度: {speed:6.2f} MB/s  (最近5秒平均: {recent_avg:6.2f} MB/s)")

            except Exception as e:
                print(f"[{int(time.time()-start_time):3d}s] 请求失败: {e}")
                speeds.append(0)

            time.sleep(1)

        print()
        print("测试完成！分析结果：")
        print()

        if speeds:
            first_10 = sum(list(speeds)[:10]) / 10
            last_10 = sum(list(speeds)[-10:]) / 10
            overall_avg = sum(speeds) / len(speeds)

            print(f"前10秒平均速度: {first_10:.2f} MB/s")
            print(f"后10秒平均速度: {last_10:.2f} MB/s")
            print(f"总体平均速度: {overall_avg:.2f} MB/s")
            print()

            # 计算衰减率
            if first_10 > 0:
                decay_rate = ((first_10 - last_10) / first_10) * 100
                print(f"速度衰减率: {decay_rate:.1f}%")

                if decay_rate > 30:
                    status = "[ERROR] 严重速度衰减，可能存在限流或连接问题"
                elif decay_rate > 10:
                    status = "[WARN] 轻度速度衰减"
                else:
                    status = "[OK] 速度稳定"

                print(f"状态: {status}")

                self.results['decay'] = {
                    'first_10': first_10,
                    'last_10': last_10,
                    'decay_rate': decay_rate,
                    'status': status
                }

        print()

    def generate_report(self):
        """生成诊断报告"""
        print("=" * 80)
        print(" " * 30 + "诊断总结")
        print("=" * 80)
        print()

        if not self.results:
            print("[ERROR] 没有诊断结果")
            return

        print("各项测试结果：")
        print()

        # DNS
        if 'dns' in self.results:
            dns = self.results['dns']
            print(f"DNS解析:    {dns['status']}")
            print(f"            平均延迟: {dns['avg']:.2f} ms")
            print()

        # TCP
        if 'tcp' in self.results:
            tcp = self.results['tcp']
            print(f"TCP连接:    {tcp['status']}")
            print(f"            失败率: {tcp['failures']}/{tcp.get('total', 10)}")
            print()

        # HTTP
        if 'http' in self.results:
            http = self.results['http']
            if 'speed_mbps' in http:
                print(f"HTTP下载:   {http['status']}")
                print(f"            速度: {http['speed_mbps']:.2f} MB/s")
                print()

        # 连接数
        if 'connections' in self.results:
            conn = self.results['connections']
            print(f"连接状态:   {conn['status']}")
            print(f"            ESTABLISHED: {conn['established']}, CLOSE_WAIT: {conn['close_wait']}")
            print()

        # 衰减
        if 'decay' in self.results:
            decay = self.results['decay']
            print(f"速度衰减:   {decay['status']}")
            print(f"            衰减率: {decay['decay_rate']:.1f}%")
            print()

        print("-" * 80)
        print()

        # 综合建议
        print("综合诊断建议：")
        print()

        issues = []
        if 'dns' in self.results and 'ERROR' in self.results['dns']['status']:
            issues.append("DNS解析速度过慢，建议使用DNS缓存服务")

        if 'tcp' in self.results and 'ERROR' in self.results['tcp']['status']:
            issues.append("TCP连接质量差，可能是网络问题或ISP限流")

        if 'connections' in self.results:
            if self.results['connections']['close_wait'] > 10:
                issues.append("发现连接泄漏，请检查是否使用最新版程序")

            if self.results['connections']['established'] > 50:
                issues.append("活跃连接数过多，建议降低并发线程数")

        if 'decay' in self.results and 'ERROR' in self.results['decay']['status']:
            issues.append("存在严重速度衰减，可能是S3限流")
            issues.append("  建议：")
            issues.append("  1. 降低线程数到2-3个")
            issues.append("  2. 每小时重启一次程序")
            issues.append("  3. 使用自适应限流")

        if issues:
            for i, issue in enumerate(issues, 1):
                print(f"{i}. {issue}")
        else:
            print("[OK] 未发现明显问题")

        print()


def main():
    """主函数"""
    print()
    print("*" * 80)
    print("*" + " " * 78 + "*")
    print("*" + " " * 20 + "S3网络诊断工具 v1.0" + " " * 36 + "*")
    print("*" + " " * 78 + "*")
    print("*" * 80)
    print()

    diagnostics = NetworkDiagnostics()

    # 运行各项测试
    diagnostics.test_dns_resolution()
    diagnostics.test_tcp_connection()

    print("是否进行HTTP下载速度测试？(可能需要一些时间)")
    choice = input("输入 Y 继续，其他键跳过: ").strip().upper()
    if choice == 'Y':
        diagnostics.test_http_download()

    diagnostics.check_active_connections()

    print()
    print("是否进行持续速度测试？（检测速度衰减，需要60秒）")
    choice = input("输入 Y 继续，其他键跳过: ").strip().upper()
    if choice == 'Y':
        diagnostics.continuous_speed_test(duration=60)

    # 生成报告
    diagnostics.generate_report()

    print()
    print("诊断完成！建议保存上述报告以便分析。")
    print()
    input("按Enter键退出...")


if __name__ == "__main__":
    main()
