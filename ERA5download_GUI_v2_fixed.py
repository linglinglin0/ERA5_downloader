import customtkinter as ctk
import boto3
from botocore import UNSIGNED
from botocore.client import Config
from botocore.exceptions import ClientError, ConnectionError, EndpointConnectionError
from boto3.s3.transfer import TransferConfig
import os
import threading
import time
import queue
import json
import traceback
import random
from concurrent.futures import ThreadPoolExecutor
from tkinter import filedialog, messagebox

# 设置外观
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# ================= 变量定义 =================
ERA5_VARS = {
    "动力与热力学": {
        "t": "空气温度 (K)", "u": "U风分量 (m/s)", "v": "V风分量 (m/s)",
        "w": "垂直速度 (Pa/s)", "z": "位势", "d": "散度", "vo": "相对涡度", "pv": "位涡"
    },
    "湿度与云物理": {
        "q": "比湿", "r": "相对湿度", "cc": "云量", "ciwc": "云冰含量",
        "clwc": "云液水含量", "crwc": "雨水含量", "cswc": "雪水含量"
    },
    "化学成分": {
        "o3": "臭氧"
    }
}

# 配置文件路径
CONFIG_FILE = ".era5_gui_config.json"


# ================= 自定义异常类 =================
class DownloadStoppedException(Exception):
    """下载被用户停止"""
    pass


class FileIncompleteException(Exception):
    """文件下载不完整"""
    pass


class ERA5ResumeDownloadApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ERA5 下载器 (支持断点续传) - 性能优化版")
        self.geometry("1150x750")

        # 拦截关闭事件
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # S3 配置
        self.bucket_name = 'nsf-ncar-era5'
        self.s3_client = None
        self.is_downloading = False
        self.stop_requested = False
        self.current_download_dir = None

        # ✅ 修复1：线程局部计数器，减少锁竞争
        self.thread_bytes = {}  # {thread_id: bytes}
        self.lock = threading.Lock()
        self.speed_reset_threshold = 1024 * 1024 * 1024  # 1GB后重置计数器

        # ✅ 修复2：批量更新进度
        self.pending_completed = []
        self.progress_lock = threading.Lock()
        self.last_progress_save = 0
        self.progress_save_interval = 30  # 30秒批量保存一次

        # 断点续传配置
        self.max_retries = 6  # 最大重试次数
        self.retry_delay = 2  # 初始重试延迟(秒)
        self.progress_file = ".era5_download_progress.json"  # 进度文件
        self.chunk_size = 8 * 1024 * 1024  # 8MB 分块大小

        # 失败文件追踪
        self.failed_files = []  # 记录下载失败的文件
        self.lock_failed = threading.Lock()  # 保护失败列表的锁

        # 布局
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ================= 左侧侧边栏 =================
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=4, sticky="nsew")

        ctk.CTkLabel(self.sidebar, text="ERA5 下载助手", font=("微软雅黑", 22, "bold")).pack(pady=30)

        # 1. 日期设置
        ctk.CTkLabel(self.sidebar, text="日期 (YYYYMM):", anchor="w").pack(fill="x", padx=20, pady=(10, 0))
        self.date_entry = ctk.CTkEntry(self.sidebar)
        self.date_entry.insert(0, "202510")
        self.date_entry.pack(fill="x", padx=20, pady=5)
        # 绑定事件：日期变化时保存配置
        self.date_entry.bind("<FocusOut>", lambda e: self.save_config())
        self.date_entry.bind("<Return>", lambda e: self.save_config())

        # 2. 路径设置
        ctk.CTkLabel(self.sidebar, text="保存根目录:", anchor="w").pack(fill="x", padx=20, pady=(15, 0))
        self.path_btn = ctk.CTkButton(self.sidebar, text="选择文件夹...", command=self.select_folder,
                                      fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"))
        self.path_btn.pack(fill="x", padx=20, pady=5)
        self.path_display = ctk.CTkLabel(self.sidebar, text="./era5_data", text_color="gray", font=("Arial", 10))
        self.path_display.pack(fill="x", padx=20)
        self.local_root = "./era5_data"

        # 3. 线程设置
        ctk.CTkLabel(self.sidebar, text="并发线程数:", anchor="w").pack(fill="x", padx=20, pady=(20, 0))
        self.thread_slider = ctk.CTkSlider(self.sidebar, from_=1, to=10, number_of_steps=9,
                                          command=self.on_slider_change)
        self.thread_slider.pack(fill="x", padx=20, pady=5)
        self.thread_slider.set(5)

        # 按钮区域
        self.start_btn = ctk.CTkButton(self.sidebar, text="开始下载", command=self.start_download,
                                       font=("微软雅黑", 15, "bold"), height=45, fg_color="#1f6aa5")
        self.start_btn.pack(fill="x", padx=20, pady=(40, 10))

        self.stop_btn = ctk.CTkButton(self.sidebar, text="停止并关闭", command=self.stop_download,
                                      font=("微软雅黑", 15, "bold"), height=45, fg_color="#a51f1f", state="disabled")
        self.stop_btn.pack(fill="x", padx=20, pady=(0, 20))

        # ================= 右侧主区域 =================
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # --- 1. 变量选择区 ---
        ctk.CTkLabel(self.main_frame, text="变量选择 (勾选即下载,全空则下载所有)", font=("微软雅黑", 16, "bold")).grid(
            row=0, column=0, padx=10, pady=10, sticky="w")

        self.scroll_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="请勾选需要的参量")
        self.scroll_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        self.checkboxes = {}
        row_idx = 0
        for category, vars_dict in ERA5_VARS.items():
            ctk.CTkLabel(self.scroll_frame, text=f"【{category}】", font=("微软雅黑", 13, "bold"),
                         text_color="#64b5f6").grid(row=row_idx, column=0, columnspan=3, sticky="w", pady=(15, 5))
            row_idx += 1
            col_idx = 0
            for var_code, var_desc in vars_dict.items():
                cb = ctk.CTkCheckBox(self.scroll_frame, text=f"{var_code.upper()} - {var_desc}", font=("Arial", 12),
                                    command=self.on_checkbox_change)
                cb.grid(row=row_idx, column=col_idx, padx=10, pady=5, sticky="w")
                self.checkboxes[var_code] = cb
                col_idx += 1
                if col_idx > 2:
                    col_idx = 0
                    row_idx += 1
            if col_idx != 0: row_idx += 1

        # --- 2. 监控面板 ---
        self.monitor_frame = ctk.CTkFrame(self.main_frame)
        self.monitor_frame.grid(row=2, column=0, padx=10, pady=(20, 10), sticky="ew")

        info_bar = ctk.CTkFrame(self.monitor_frame, fg_color="transparent")
        info_bar.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(info_bar, text="下载进度监控", font=("微软雅黑", 14, "bold")).pack(side="left")
        self.speed_label = ctk.CTkLabel(info_bar, text="当前速度: 0.0 MB/s", font=("Consolas", 14, "bold"),
                                        text_color="#00e676")
        self.speed_label.pack(side="right")

        self.slots = []
        for i in range(10):
            f = ctk.CTkFrame(self.monitor_frame, fg_color="transparent")
            f.pack(fill="x", pady=2)
            lbl = ctk.CTkLabel(f, text=f"线程-{i + 1}: 闲置", width=280, anchor="w", font=("Consolas", 11))
            lbl.pack(side="left")
            bar = ctk.CTkProgressBar(f, height=10)
            bar.pack(side="left", fill="x", expand=True, padx=10)
            bar.set(0)
            pct = ctk.CTkLabel(f, text="0%", width=80)
            pct.pack(side="left")
            self.slots.append({"frame": f, "label": lbl, "bar": bar, "pct": pct})
            f.pack_forget()

        self.log_label = ctk.CTkLabel(self.monitor_frame, text="系统日志: 就绪", text_color="gray", anchor="w")
        self.log_label.pack(fill="x", padx=10, pady=5)

        # 加载保存的配置
        self.load_config()

    # ================= 配置管理 =================

    def save_config(self):
        """保存当前配置到文件"""
        try:
            config = {
                'date': self.date_entry.get(),
                'local_root': self.local_root,
                'thread_count': int(self.thread_slider.get()),
                'selected_vars': [k for k, v in self.checkboxes.items() if v.get() == 1]
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def load_config(self):
        """从文件加载配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 恢复日期
                if 'date' in config:
                    self.date_entry.delete(0, 'end')
                    self.date_entry.insert(0, config['date'])

                # 恢复路径
                if 'local_root' in config:
                    self.local_root = config['local_root']
                    display_text = config['local_root'] if len(config['local_root']) < 40 else "..." + config['local_root'][-35:]
                    self.path_display.configure(text=display_text)

                # 恢复线程数
                if 'thread_count' in config:
                    self.thread_slider.set(config['thread_count'])

                # 恢复变量选择
                if 'selected_vars' in config:
                    for var_code in config['selected_vars']:
                        if var_code in self.checkboxes:
                            self.checkboxes[var_code].select()

                print("配置已加载")
        except Exception as e:
            print(f"加载配置失败: {e}")

    def on_slider_change(self, value):
        """滑块变化回调"""
        # 延迟保存，避免频繁写入
        self.after(500, self.save_config)

    def on_checkbox_change(self):
        """复选框变化回调"""
        # 延迟保存，避免频繁写入
        self.after(500, self.save_config)

    def on_closing(self):
        """窗口关闭事件"""
        if self.is_downloading:
            # 如果正在下载，调用停止下载
            self.stop_download()
        else:
            # 如果没有下载，直接保存配置并退出
            self.save_config()
            self.destroy()

    # ================= 逻辑功能 =================

    def select_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.local_root = d
            self.path_display.configure(text=d if len(d) < 40 else "..." + d[-35:])
            # 保存配置
            self.save_config()

    def get_selected_vars(self):
        return [k for k, v in self.checkboxes.items() if v.get() == 1]

    def save_progress(self, progress_data):
        """保存下载进度到文件"""
        try:
            progress_file = os.path.join(self.current_download_dir, self.progress_file)
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存进度失败: {e}")

    def load_progress(self, target_dir):
        """从文件加载下载进度"""
        try:
            progress_file = os.path.join(target_dir, self.progress_file)
            if os.path.exists(progress_file):
                with open(progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载进度失败: {e}")
        return None

    def stop_download(self):
        """停止下载,保留临时文件供断点续传"""
        self.stop_requested = True

        # UI反馈
        self.log_label.configure(text="正在停止,保留临时文件供续传...", text_color="orange")
        self.stop_btn.configure(text="停止中...", state="disabled")

        # 保存配置
        self.save_config()

        # ✅ 保存待处理的进度
        if self.current_download_dir:
            self._flush_progress(self.current_download_dir)

        # 等待线程结束(最多5秒)
        for _ in range(50):
            if not self.is_downloading:
                break
            time.sleep(0.1)

        # 关闭网络
        if self.s3_client:
            try:
                self.s3_client._endpoint.http_session.close()
            except:
                pass

        # 关闭窗口
        self.destroy()
        os._exit(0)

    def start_download(self):
        if self.is_downloading: return
        date_str = self.date_entry.get().strip()
        if len(date_str) != 6:
            messagebox.showerror("错误", "日期格式不正确")
            return

        # 保存配置
        self.save_config()

        self.is_downloading = True
        self.stop_requested = False
        self.total_bytes = 0
        self.last_bytes = 0
        self.thread_bytes = {}  # ✅ 重置线程计数器

        self.start_btn.configure(state="disabled", text="运行中...")
        self.stop_btn.configure(state="normal", text="停止并关闭")

        num_threads = int(self.thread_slider.get())
        for i in range(10):
            if i < num_threads:
                self.slots[i]['frame'].pack(fill="x")
            else:
                self.slots[i]['frame'].pack_forget()

        threading.Thread(target=self.run_logic, args=(date_str, num_threads), daemon=True).start()
        self.monitor_speed()

    def monitor_speed(self):
        if not self.is_downloading:
            self.speed_label.configure(text="当前速度: 0.0 MB/s")
            return

        # ✅ 使用线程局部计数器汇总
        with self.lock:
            curr = sum(self.thread_bytes.values()) + self.total_bytes
        diff = curr - self.last_bytes
        self.last_bytes = curr

        # 定期重置total_bytes，避免数值过大影响性能
        if curr > self.speed_reset_threshold:
            with self.lock:
                self.total_bytes = 0
                self.thread_bytes.clear()
                self.last_bytes = 0

        self.speed_label.configure(text=f"当前速度: {diff / 1048576:.2f} MB/s")
        self.after(1000, self.monitor_speed)

    def run_logic(self, date_str, max_workers):
        try:
            prefix = f"e5.oper.an.pl/{date_str}/"

            # ✅ 修复3：优化S3客户端配置
            s3_config = Config(
                signature_version=UNSIGNED,
                max_pool_connections=max_workers * 4,  # ✅ 增加到4倍
                tcp_keepalive=True,
                connect_timeout=15,  # ✅ 从10增加到15
                read_timeout=60,  # ✅ 从30增加到60
                retries={'max_attempts': 2}
            )
            self.s3_client = boto3.client('s3', config=s3_config)

            wanted_vars = self.get_selected_vars()
            self.log_label.configure(text=f"正在扫描... 目标变量: {wanted_vars if wanted_vars else '全部'}",
                                     text_color="#64b5f6")

            # 清空失败文件列表和待处理列表
            with self.lock_failed:
                self.failed_files.clear()
            with self.progress_lock:
                self.pending_completed.clear()
            self.last_progress_save = time.time()

            paginator = self.s3_client.get_paginator('list_objects_v2')
            files_to_download = []

            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        fname = os.path.basename(key)
                        try:
                            parts = fname.split('.')
                            var_segment = parts[4]
                            current_var = var_segment.split('_')[-1]
                        except:
                            current_var = "unknown"

                        if not wanted_vars or current_var in wanted_vars:
                            files_to_download.append(
                                {'Key': key, 'Size': obj['Size'], 'Var': current_var, 'Name': fname})

            if not files_to_download:
                self.log_label.configure(text="未找到文件!", text_color="red")
                self.reset_ui()
                return

            target_dir = os.path.join(self.local_root, date_str)
            if not os.path.exists(target_dir): os.makedirs(target_dir)
            self.current_download_dir = target_dir

            # 加载之前的进度
            progress_data = self.load_progress(target_dir)
            completed_files = set()
            if progress_data and 'completed' in progress_data:
                completed_files = set(progress_data['completed'])

            # 过滤已完成的文件
            remaining_files = [f for f in files_to_download if f['Name'] not in completed_files]

            if not remaining_files:
                self.log_label.configure(text="所有文件已下载完成!", text_color="#00e676")
                messagebox.showinfo("提示", f"所有文件已下载完成: {target_dir}")
                self.reset_ui()
                return

            self.log_label.configure(
                text=f"共 {len(files_to_download)} 个文件,已完成 {len(completed_files)},剩余 {len(remaining_files)}",
                text_color="white"
            )

            slot_queue = queue.Queue()
            for i in range(max_workers):
                slot_queue.put(i)

            transfer_cfg = TransferConfig(use_threads=False)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for f_info in remaining_files:
                    if self.stop_requested: break
                    futures.append(executor.submit(
                        self.download_one_with_resume, f_info, target_dir, transfer_cfg, slot_queue
                    ))

                # 等待所有任务完成
                for i, f in enumerate(futures):
                    try:
                        f.result()
                    except DownloadStoppedException:
                        # 用户停止下载，不记录为失败
                        pass
                    except Exception as e:
                        # 其他异常已经记录在 failed_files 中
                        print(f"任务异常: {e}")

            if not self.stop_requested:
                # ✅ 最后一次保存进度
                self._flush_progress(target_dir)

                # 清理进度文件
                progress_file = os.path.join(target_dir, self.progress_file)
                if os.path.exists(progress_file):
                    try:
                        os.remove(progress_file)
                    except:
                        pass

                # 检查是否有失败的文件
                with self.lock_failed:
                    failed_count = len(self.failed_files)

                if failed_count > 0:
                    # 有文件下载失败
                    self.log_label.configure(
                        text=f"下载完成，但 {failed_count} 个文件失败",
                        text_color="orange"
                    )

                    # 构建失败文件列表
                    failure_list = "以下文件下载失败:\n\n"
                    with self.lock_failed:
                        for i, f in enumerate(self.failed_files[:10]):  # 只显示前10个
                            failure_list += f"{i+1}. {f['name']}\n"
                            failure_list += f"   错误: {f['error']}\n"
                            if 'size' in f:
                                failure_list += f"   进度: {f['size']}/{f['expected']} 字节\n"
                            failure_list += "\n"

                        if failed_count > 10:
                            failure_list += f"... 还有 {failed_count - 10} 个文件失败\n"

                    messagebox.showwarning("部分文件下载失败", failure_list)
                else:
                    # 所有文件都成功
                    self.log_label.configure(text="所有任务完成!", text_color="#00e676")
                    messagebox.showinfo("成功", f"文件已保存至: {target_dir}")

        except Exception as e:
            self.log_label.configure(text=f"错误: {str(e)}", text_color="red")
            print(e)
        finally:
            self.reset_ui()

    def download_one_with_resume(self, f_info, target_dir, cfg, slot_queue):
        """支持断点续传的下载方法"""
        if self.stop_requested:
            raise DownloadStoppedException("用户停止下载")

        sid = slot_queue.get()
        local_path = os.path.join(target_dir, f_info['Name'])
        temp_path = local_path + ".tmp"
        short_name = f_info['Name'][-25:]

        try:
            if self.stop_requested:
                raise DownloadStoppedException("用户停止下载")

            # 检查本地文件是否完整
            if os.path.exists(local_path):
                local_size = os.path.getsize(local_path)
                remote_size = f_info['Size']
                if local_size == remote_size:
                    self.update_slot(sid, f_info['Var'], short_name, 1.0, "已存在(跳过)")
                    self._update_progress(target_dir, f_info['Name'], completed=True)
                    return
                else:
                    self.update_slot(sid, f_info['Var'], short_name, 0, "不完整-重下")

            # 检查临时文件大小(断点续传)
            downloaded_bytes = 0
            if os.path.exists(temp_path):
                downloaded_bytes = os.path.getsize(temp_path)
                if downloaded_bytes > 0 and downloaded_bytes < f_info['Size']:
                    pct = downloaded_bytes / f_info['Size']
                    self.update_slot(sid, f_info['Var'], short_name, pct,
                                   f"断点续传 {self._format_size(downloaded_bytes)}")
                else:
                    # 临时文件无效,删除
                    os.remove(temp_path)
                    downloaded_bytes = 0
                    self.update_slot(sid, f_info['Var'], short_name, 0, "开始下载...")
            else:
                self.update_slot(sid, f_info['Var'], short_name, 0, "开始下载...")

            # 使用 Range 请求进行断点续传
            self._download_with_retry(f_info, temp_path, downloaded_bytes, sid)

            # 下载完成,重命名文件
            if not self.stop_requested and os.path.exists(temp_path):
                # 验证文件大小
                final_size = os.path.getsize(temp_path)
                if final_size == f_info['Size']:
                    os.rename(temp_path, local_path)
                    self.update_slot(sid, f_info['Var'], short_name, 1.0, "完成")
                    # 更新进度
                    self._update_progress(target_dir, f_info['Name'], completed=True)
                else:
                    # 文件不完整，抛出异常
                    error_msg = f"文件大小不匹配: 期望{f_info['Size']}字节，实际{final_size}字节"
                    raise FileIncompleteException(error_msg)

        except DownloadStoppedException:
            # 用户停止下载，保留临时文件
            self.update_slot(sid, f_info['Var'], short_name, 0, "已停止")
            raise  # 重新抛出，让调用者知道这是用户停止

        except FileIncompleteException as e:
            # 文件下载不完整
            failure_info = {
                'name': f_info['Name'],
                'error': str(e),
                'size': os.path.getsize(temp_path) if os.path.exists(temp_path) else 0,
                'expected': f_info['Size']
            }
            with self.lock_failed:
                self.failed_files.append(failure_info)

            # 记录详细错误日志
            self._log_error(f_info, e, traceback.format_exc())

            self.update_slot(sid, f_info['Var'], short_name, 0, "文件不完整")
            # 不抛出异常，保留临时文件供续传

        except Exception as e:
            # 其他异常
            failure_info = {
                'name': f_info['Name'],
                'error': f"{type(e).__name__}: {str(e)}",
                'size': os.path.getsize(temp_path) if os.path.exists(temp_path) else 0,
                'expected': f_info['Size']
            }
            with self.lock_failed:
                self.failed_files.append(failure_info)

            # 记录详细错误日志
            self._log_error(f_info, e, traceback.format_exc())

            self.update_slot(sid, "Err", "失败", 0, f"{type(e).__name__}")
            # 不抛出异常，继续下载其他文件

        finally:
            slot_queue.put(sid)

    def _download_with_retry(self, f_info, temp_path, start_byte, sid):
        """✅ 修复4：带重试的下载方法（关键修复：关闭HTTP响应）"""
        short_name = f_info['Name'][-25:]
        remote_size = f_info['Size']
        thread_id = threading.get_ident()

        # ✅ 初始化线程计数器
        if thread_id not in self.thread_bytes:
            with self.lock:
                if thread_id not in self.thread_bytes:
                    self.thread_bytes[thread_id] = 0

        for retry in range(self.max_retries):
            # 检查是否停止请求
            if self.stop_requested:
                raise DownloadStoppedException("用户停止下载")

            response = None  # ✅ 关键：在外面声明，以便finally中访问

            try:
                if start_byte >= remote_size:
                    # 文件已经下载完成
                    return

                # 使用 Range 请求
                range_header = f"bytes={start_byte}-"

                # 获取对象
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=f_info['Key'],
                    Range=range_header
                )

                # 写入文件(追加模式)
                mode = 'ab' if start_byte > 0 else 'wb'
                with open(temp_path, mode) as f:
                    downloaded = start_byte
                    chunk_size = self.chunk_size
                    chunk_count = 0

                    for chunk in response['Body'].iter_chunks(chunk_size=chunk_size):
                        # 检查是否停止请求
                        if self.stop_requested:
                            raise DownloadStoppedException("用户停止下载")

                        f.write(chunk)
                        downloaded += len(chunk)
                        chunk_count += 1

                        # ✅ 修复5：线程局部计数，减少锁竞争
                        self.thread_bytes[thread_id] += len(chunk)

                        # ✅ 定期汇总到全局（每100个chunk）
                        if chunk_count % 100 == 0:
                            with self.lock:
                                local_total = sum(self.thread_bytes.values())
                                self.total_bytes = local_total

                        pct = downloaded / remote_size
                        t = time.time()
                        # 动态调整UI更新频率：大文件更新频率低，小文件更新频率高
                        update_interval = max(0.2, min(1.0, remote_size / 100_000_000))
                        if t - cb.last_t > update_interval or pct >= 1.0:
                            # 显示百分比和已下载大小
                            status_text = f"{int(pct * 100)}%"
                            if retry > 0:
                                status_text += f" (重试{retry+1})"
                            self.update_slot(sid, f_info['Var'], short_name, pct, status_text)
                            cb.last_t = t

                # 下载成功,退出重试循环
                return

            except DownloadStoppedException:
                # 用户停止，重新抛出
                raise

            except (ConnectionError, ClientError, EndpointConnectionError, OSError, IOError) as e:
                if retry < self.max_retries - 1:
                    # ✅ 修复6：添加抖动，避免重试风暴
                    delay = self.retry_delay * (2 ** retry)
                    jitter = random.uniform(0.8, 1.2)  # ±20%抖动
                    actual_delay = delay * jitter

                    # 计算当前进度
                    current_pct = 0
                    if os.path.exists(temp_path):
                        current_size = os.path.getsize(temp_path)
                        current_pct = current_size / remote_size

                    self.update_slot(sid, f_info['Var'], short_name, current_pct,
                                   f"网络错误,{int(actual_delay)}秒后重试({retry+1}/{self.max_retries})")
                    time.sleep(actual_delay)

                    # 更新断点位置
                    if os.path.exists(temp_path):
                        start_byte = os.path.getsize(temp_path)
                else:
                    # 达到最大重试次数，重新抛出异常
                    raise

            finally:
                # ✅✅✅ 关键修复：确保关闭HTTP响应，释放连接
                if response is not None:
                    try:
                        response['Body'].close()
                    except:
                        pass

    def _update_progress(self, target_dir, filename, completed=False):
        """✅ 修复7：批量更新下载进度"""
        if completed:
            with self.progress_lock:
                self.pending_completed.append(filename)

                # 定期批量保存（每30秒）
                now = time.time()
                if now - self.last_progress_save > self.progress_save_interval:
                    self._flush_progress(target_dir)
                    self.last_progress_save = now

    def _flush_progress(self, target_dir):
        """批量保存进度"""
        with self.progress_lock:
            if not self.pending_completed:
                return

            progress_data = self.load_progress(target_dir)
            if progress_data is None:
                progress_data = {'completed': [], 'date': time.strftime('%Y-%m-%d %H:%M:%S')}

            # 批量添加
            for filename in self.pending_completed:
                if filename not in progress_data['completed']:
                    progress_data['completed'].append(filename)

            self.save_progress(progress_data)
            self.pending_completed.clear()

    def _log_error(self, f_info, exception, traceback_str):
        """记录错误日志到文件"""
        try:
            error_log_file = "download_errors.log"
            with open(error_log_file, 'a', encoding='utf-8') as log:
                log.write(f"\n{'='*80}\n")
                log.write(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                log.write(f"文件: {f_info['Name']}\n")
                log.write(f"变量: {f_info['Var']}\n")
                log.write(f"大小: {f_info['Size']} 字节\n")
                log.write(f"异常: {type(exception).__name__}: {str(exception)}\n")
                log.write(f"堆栈:\n{traceback_str}\n")
                log.write(f"{'='*80}\n")
        except Exception as e:
            # 如果日志记录失败，至少输出到控制台
            print(f"记录错误日志失败: {e}")
            print(f"原始错误: {exception}")

    def _format_size(self, bytes_size):
        """格式化文件大小显示"""
        if bytes_size < 1024 * 1024:
            return f"{bytes_size / 1024:.1f}KB"
        else:
            return f"{bytes_size / 1048576:.1f}MB"

    def update_slot(self, sid, var, name, pct, status=None):
        def _ui():
            # 如果提供了状态文本，使用状态文本；否则显示百分比
            if status:
                txt = status
            else:
                txt = f"{int(pct * 100)}%"

            self.slots[sid]['label'].configure(text=f"[{var}] ...{name}")
            self.slots[sid]['bar'].set(pct)
            self.slots[sid]['pct'].configure(text=txt)

        self.after(0, _ui)

    def reset_ui(self):
        self.is_downloading = False

        def _r():
            self.start_btn.configure(state="normal", text="开始下载")
            self.stop_btn.configure(state="disabled", text="停止并关闭")
            self.speed_label.configure(text="当前速度: 0.0 MB/s")
            for s in self.slots:
                s['label'].configure(text="闲置")
                s['bar'].set(0)
                s['pct'].configure(text="0%")

        self.after(0, _r)


# 全局回调对象(用于进度更新)
class CallbackWrapper:
    def __init__(self):
        self.done = 0
        self.last_t = 0

cb = CallbackWrapper()


if __name__ == "__main__":
    app = ERA5ResumeDownloadApp()
    app.mainloop()
