#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ERA5下载软件 - 错误日志分析工具
快速分析已有的错误日志，诊断问题
"""

import os
import re
from datetime import datetime
from collections import defaultdict, Counter

class ErrorLogAnalyzer:
    """错误日志分析器"""

    def __init__(self, log_file="download_errors.log"):
        self.log_file = log_file
        self.errors = []

    def parse_log(self):
        """解析错误日志"""
        if not os.path.exists(self.log_file):
            print(f"[错误] 未找到错误日志文件: {self.log_file}")
            print("   请先运行下载程序，产生错误后再使用此工具")
            return False

        print(f"[信息] 正在读取错误日志: {self.log_file}")

        with open(self.log_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 分割错误记录
        error_blocks = re.split(r'=+', content)

        for block in error_blocks:
            if not block.strip():
                continue

            error_info = self._parse_error_block(block)
            if error_info:
                self.errors.append(error_info)

        print(f"[成功] 成功解析 {len(self.errors)} 条错误记录\n")
        return len(self.errors) > 0

    def _parse_error_block(self, block):
        """解析单个错误块"""
        info = {
            'time': None,
            'filename': None,
            'variable': None,
            'size': None,
            'exception': None,
            'traceback': None
        }

        # 提取时间
        time_match = re.search(r'时间:\s*(.+)', block)
        if time_match:
            info['time'] = time_match.group(1).strip()

        # 提取文件名
        file_match = re.search(r'文件:\s*(.+)', block)
        if file_match:
            info['filename'] = file_match.group(1).strip()

        # 提取变量
        var_match = re.search(r'变量:\s*(.+)', block)
        if var_match:
            info['variable'] = var_match.group(1).strip()

        # 提取大小
        size_match = re.search(r'大小:\s*(\d+)\s*字节', block)
        if size_match:
            info['size'] = int(size_match.group(1))

        # 提取异常
        exc_match = re.search(r'异常:\s*(.+)', block)
        if exc_match:
            info['exception'] = exc_match.group(1).strip()

        # 提取堆栈
            tb_match = re.search(r'堆栈:\s*(.+?)(?=={80,}|$)', block, re.DOTALL)
            if tb_match:
                info['traceback'] = tb_match.group(1).strip()

        return info if info['exception'] else None

    def analyze_error_types(self):
        """分析错误类型分布"""
        print("=" * 80)
        print("【错误类型统计】")
        print("=" * 80)
        print()

        error_types = Counter()
        for error in self.errors:
            # 提取异常类型
            exc = error['exception']
            if exc:
                # 提取异常类名（如 "ConnectionError"）
                type_match = re.match(r'(\w+):', exc)
                if type_match:
                    error_types[type_match.group(1)] += 1
                else:
                    error_types[exc.split(':')[0]] += 1

        if not error_types:
            print("  [OK] 没有检测到明确错误类型")
            return

        total = sum(error_types.values())
        print(f"总错误数: {total}\n")
        print(f"{'错误类型':<30} {'次数':>10} {'占比':>10} {'严重程度':>10}")
        print("-" * 80)

        severity_map = {
            'ConnectionError': '[高]',
            'TimeoutError': '[高]',
            'EndpointConnectionError': '[高]',
            'ClientError': '[中]',
            'FileIncompleteException': '[中]',
            'OSError': '[中]',
            'IOError': '[中]',
            'DownloadStoppedException': '[低]',
        }

        for error_type, count in error_types.most_common():
            percent = count / total * 100
            severity = severity_map.get(error_type, '[未知]')
            print(f"{error_type:<30} {count:>10} {percent:>9.1f}% {severity:>10}")

        print()

        # 诊断建议
        network_errors = error_types.get('ConnectionError', 0) + \
                        error_types.get('EndpointConnectionError', 0) + \
                        error_types.get('TimeoutError', 0)

        if network_errors > total * 0.5:
            print("[诊断] 超过50%%的错误是网络相关")
            print("[可能原因]:")
            print("   1. HTTP响应未正确关闭导致连接泄漏")
            print("   2. 连接池大小不足")
            print("   3. 网络超时设置过短")
            print()
            print("[建议]:")
            print("   - 添加 response['Body'].close()")
            print("   - 增加 max_pool_connections")
            print("   - 增加超时时间到60秒")
            print()

    def analyze_time_pattern(self):
        """分析时间模式"""
        print("=" * 80)
        print("【错误时间分布】")
        print("=" * 80)
        print()

        if not self.errors:
            return

        # 按小时统计
        hour_counts = defaultdict(int)
        for error in self.errors:
            if error['time']:
                try:
                    dt = datetime.strptime(error['time'], '%Y-%m-%d %H:%M:%S')
                    hour_counts[dt.hour] += 1
                except:
                    pass

        if hour_counts:
            print(f"{'小时':<10} {'错误次数':>15}")
            print("-" * 80)
            for hour in sorted(hour_counts.keys()):
                print(f"{hour:02d}:00-{hour:02d}:59  {hour_counts[hour]:>15}")

            print()

            # 分析趋势
            hours = sorted(hour_counts.keys())
            if len(hours) >= 2:
                early_avg = sum(hour_counts[h] for h in hours[:len(hours)//2]) / (len(hours)//2)
                late_avg = sum(hour_counts[h] for h in hours[len(hours)//2:]) / (len(hours) - len(hours)//2)

                print(f"前期平均错误/小时: {early_avg:.1f}")
                print(f"后期平均错误/小时: {late_avg:.1f}")

                if late_avg > early_avg * 1.5:
                    print()
                    print("[诊断] 错误率随时间上升")
                    print("[分析] 这表明存在资源泄漏或连接池耗尽问题")
                    print()

    def analyze_files(self):
        """分析问题文件"""
        print("=" * 80)
        print("【问题文件分析】")
        print("=" * 80)
        print()

        if not self.errors:
            return

        # 统计重复失败的文件
        file_errors = defaultdict(int)
        for error in self.errors:
            if error['filename']:
                file_errors[error['filename']] += 1

        # 找出最常失败的文件
        if file_errors:
            print(f"{'最常失败的文件（前10个）':<50} {'失败次数':>10}")
            print("-" * 80)

            for filename, count in sorted(file_errors.items(), key=lambda x: -x[1])[:10]:
                display_name = filename if len(filename) < 47 else '...' + filename[-44:]
                print(f"{display_name:<50} {count:>10}")

            print()

            # 检查是否有文件反复失败
            repeated_failures = [f for f, c in file_errors.items() if c >= 3]
            if repeated_failures:
                print(f"[警告] 发现 {len(repeated_failures)} 个文件反复失败3次或以上")
                print("[建议] 这些文件可能因为网络问题一直无法完成下载")
                print("        建议: 检查这些文件的Range请求是否正确")
                print()

    def analyze_retries(self):
        """分析重试情况"""
        print("=" * 80)
        print("【重试与恢复分析】")
        print("=" * 80)
        print()

        # 统计包含"重试"的错误
        retry_count = 0
        for error in self.errors:
            if error['traceback'] and 'retry' in error['traceback'].lower():
                retry_count += 1

        if retry_count > 0:
            print(f"涉及重试的错误: {retry_count} 次")

            # 估算重试开销
            # 假设平均每次错误触发2次重试，每次平均10秒
            estimated_waste = retry_count * 2 * 10
            print(f"估算重试浪费: {estimated_waste} 秒 ({estimated_waste/60:.1f} 分钟)")
            print()

        # 分析重试成功率
        connection_errors = sum(1 for e in self.errors if e['exception'] and
                               any(t in e['exception'] for t in
                                   ['ConnectionError', 'EndpointConnectionError', 'TimeoutError']))

        if connection_errors > 0:
            print(f"网络相关错误: {connection_errors} 次")

            # 如果网络错误占比高
            if connection_errors > len(self.errors) * 0.5:
                print()
                print("[严重警告] 超过一半的错误是网络连接问题")
                print("[分析] 这通常表明:")
                print("   1. HTTP响应未关闭 -> 连接泄漏")
                print("   2. 连接池配置不足")
                print("   3. 没有有效的连接复用")
                print()
                print("[紧急修复措施]:")
                print("   优先级1: 添加 response['Body'].close()")
                print("   优先级2: 增加 max_pool_connections 到 workers*4")
                print("   优先级3: 增加超时时间")
                print()

    def generate_diagnosis_report(self):
        """生成诊断报告"""
        print()
        print("=" * 80)
        print(" " * 20 + "综合诊断报告")
        print("=" * 80)
        print()

        if not self.errors:
            print("[OK] 未发现错误日志，系统运行正常！")
            return

        # 计算关键指标
        total_errors = len(self.errors)

        network_errors = sum(1 for e in self.errors if e['exception'] and
                            any(t in e['exception'] for t in
                                ['ConnectionError', 'EndpointConnectionError',
                                 'TimeoutError', 'ClientError']))

        network_error_rate = network_errors / total_errors * 100 if total_errors > 0 else 0

        # 诊断结论
        print("【诊断结论】")
        print()

        if network_error_rate > 70:
            print("[严重问题] 连接泄漏导致性能恶化")
            print()
            print("   问题特征:")
            print(f"   - {network_error_rate:.1f}%% 的错误是网络连接问题")
            print("   - 随着时间推移错误率上升")
            print("   - 大量重试浪费时间")
            print()
            print("   根本原因:")
            print("   1. HTTP响应对象未关闭，连接无法返回池中")
            print("   2. 连接池逐渐耗尽，新请求失败")
            print("   3. 指数退避重试浪费大量时间")
            print()
            print("   [紧急修复]（预计提升50-70%%性能）:")
            print("   - 在 finally 块中添加 response['Body'].close()")
            print("   - 增加连接池大小: max_workers * 4")
            print("   - 优化重试策略，添加随机抖动")

        elif network_error_rate > 40:
            print("[中等问题] 网络连接不稳定")
            print()
            print("   问题特征:")
            print(f"   - {network_error_rate:.1f}%% 的错误与网络有关")
            print()
            print("   可能原因:")
            print("   - 连接池配置偏小")
            print("   - 超时时间设置过短")
            print("   - 网络质量不稳定")
            print()
            print("   [建议修复]:")
            print("   - 增加连接池大小")
            print("   - 调整超时配置")
            print("   - 添加连接健康检查")

        else:
            print("[系统状态] 可接受")
            print()
            print("   错误类型多样，可能是偶发问题")
            print("   建议继续监控")

        print()
        print("=" * 80)

    def analyze(self):
        """执行完整分析"""
        if not self.parse_log():
            return

        self.analyze_error_types()
        self.analyze_time_pattern()
        self.analyze_files()
        self.analyze_retries()
        self.generate_diagnosis_report()


def main():
    """主函数"""
    print("=" * 80)
    print(" " * 20 + "ERA5错误日志分析工具")
    print("=" * 80)
    print()

    analyzer = ErrorLogAnalyzer()
    analyzer.analyze()

    print()
    print("分析完成！")
    print()
    print("下一步操作:")
    print("  1. 查看上述诊断报告，了解问题严重程度")
    print("  2. 根据建议决定是否需要修复代码")
    print("  3. 如果需要修复，可以联系开发人员")


if __name__ == "__main__":
    main()
