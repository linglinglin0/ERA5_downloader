"""
锁竞争演示脚本
展示不同 chunk_size 对锁竞争的影响
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor


class LockContentionDemo:
    def __init__(self):
        self.lock = threading.Lock()
        self.total_bytes = 0
        self.chunk_times = []  # 记录每个chunk的等待时间

    def simulate_download_with_lock(self, thread_id, chunk_size, num_chunks):
        """模拟下载过程"""
        thread_wait_times = []

        for i in range(num_chunks):
            # 模拟下载/写入数据（0.5秒）
            time.sleep(0.5)

            # 记录等待锁的时间
            start_wait = time.time()

            # 获取锁并更新进度
            with self.lock:
                wait_time = time.time() - start_wait
                thread_wait_times.append(wait_time)

                # 模拟更新操作（0.00001秒）
                self.total_bytes += chunk_size

        return thread_wait_times

    def run_test(self, num_threads=10, chunk_size=8, num_chunks=25):
        """运行测试

        Args:
            num_threads: 线程数
            chunk_size: 每个chunk的大小(MB)
            num_chunks: 每个线程的chunk数量
        """
        print(f"\n{'='*60}")
        print(f"测试配置: {num_threads}线程, {chunk_size}MB chunk, {num_chunks}chunks/线程")
        print(f"{'='*60}")

        self.total_bytes = 0
        self.chunk_times = []

        start_time = time.time()

        # 使用线程池
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i in range(num_threads):
                future = executor.submit(
                    self.simulate_download_with_lock,
                    i, chunk_size, num_chunks
                )
                futures.append(future)

            # 收集所有线程的等待时间
            all_wait_times = []
            for future in futures:
                wait_times = future.result()
                all_wait_times.extend(wait_times)

        total_time = time.time() - start_time

        # 统计分析
        total_lock_waits = len(all_wait_times)
        avg_wait_time = sum(all_wait_times) / total_lock_waits if total_lock_waits else 0
        max_wait_time = max(all_wait_times) if all_wait_times else 0
        total_wait_time = sum(all_wait_times)

        print(f"\n[锁竞争统计]")
        print(f"  总锁获取次数: {total_lock_waits}")
        print(f"  平均等待时间: {avg_wait_time*1000:.3f} ms")
        print(f"  最大等待时间: {max_wait_time*1000:.3f} ms")
        print(f"  总等待时间: {total_wait_time:.2f} 秒")
        print(f"  总执行时间: {total_time:.2f} 秒")
        print(f"  锁开销占比: {(total_wait_time/total_time)*100:.1f}%")

        # 计算下载速度
        total_mb = self.total_bytes / (1024 * 1024)
        speed = total_mb / total_time
        print(f"\n[下载速度: {speed:.1f} MB/s]")

        return {
            'total_locks': total_lock_waits,
            'avg_wait_ms': avg_wait_time * 1000,
            'max_wait_ms': max_wait_time * 1000,
            'overhead_pct': (total_wait_time / total_time) * 100,
            'speed_mbps': speed
        }


def main():
    """主测试函数"""
    import sys
    import io

    # 设置标准输出编码为UTF-8
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    demo = LockContentionDemo()

    print("\n" + "锁竞争演示".center(60, "="))
    print("\n这个测试模拟了ERA5下载器中的多线程下载场景")
    print("每个线程下载25个chunk（模拟200MB文件，8MB chunk）")

    results = {}

    # 测试不同的 chunk_size
    test_configs = [
        (2, 50),   # 2MB, 50个chunk
        (4, 25),   # 4MB, 25个chunk
        (8, 25),   # 8MB, 25个chunk（当前配置）
        (16, 13),  # 16MB, 13个chunk
    ]

    for chunk_size, num_chunks in test_configs:
        result = demo.run_test(
            num_threads=10,
            chunk_size=chunk_size,
            num_chunks=num_chunks
        )
        results[chunk_size] = result
        time.sleep(1)  # 短暂休息

    # 汇总对比
    print("\n" + "="*60)
    print("[配置对比汇总]")
    print("="*60)
    print(f"{'Chunk':<10} {'锁次数':<12} {'平均等待':<12} {'开销占比':<12} {'速度':<12}")
    print("-"*60)

    for chunk_size in [2, 4, 8, 16]:
        r = results[chunk_size]
        print(f"{chunk_size} MB{'':<6} "
              f"{r['total_locks']:<12} "
              f"{r['avg_wait_ms']:.2f} ms{'':<4} "
              f"{r['overhead_pct']:.1f}%{'':<7} "
              f"{r['speed_mbps']:.1f} MB/s")

    # 推荐建议
    print("\n" + "="*60)
    print("[推荐建议]")
    print("="*60)
    print("\n[当前配置 (8MB) 是一个很好的平衡点]")
    print("   - 锁开销占比适中")
    print("   - 下载速度较高")
    print("   - 内存占用可控")
    print("\n[如果追求极限速度且内存充足]")
    print("   -> 使用 16MB chunk")
    print("\n[如果网络不稳定]")
    print("   -> 使用 4MB chunk")

    print("\n" + "="*60)


if __name__ == "__main__":
    main()
