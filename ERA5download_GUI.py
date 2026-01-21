import customtkinter as ctk
import boto3
from botocore import UNSIGNED
from botocore.client import Config
from boto3.s3.transfer import TransferConfig
import os
import threading
import time
import queue
import glob
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


class ERA5CleanStopApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ERA5 下载器")
        self.geometry("1150x750")

        # 拦截关闭事件
        self.protocol("WM_DELETE_WINDOW", self.stop_download)

        # S3 配置
        self.bucket_name = 'nsf-ncar-era5'
        self.s3_client = None
        self.is_downloading = False
        self.stop_requested = False
        self.current_download_dir = None  # 记录当前下载目录

        # 速度监控锁
        self.total_bytes = 0
        self.last_bytes = 0
        self.lock = threading.Lock()

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
        self.thread_slider = ctk.CTkSlider(self.sidebar, from_=1, to=10, number_of_steps=9)
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
        ctk.CTkLabel(self.main_frame, text="变量选择 (勾选即下载，全空则下载所有)", font=("微软雅黑", 16, "bold")).grid(
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
                cb = ctk.CTkCheckBox(self.scroll_frame, text=f"{var_code.upper()} - {var_desc}", font=("Arial", 12))
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

    # ================= 逻辑功能 =================

    def select_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.local_root = d
            self.path_display.configure(text=d if len(d) < 40 else "..." + d[-35:])

    def get_selected_vars(self):
        return [k for k, v in self.checkboxes.items() if v.get() == 1]

    def stop_download(self):
        """
        停止下载，强制关闭，并清理所有包含 .tmp 的文件
        """
        # 1. 标记
        self.stop_requested = True

        # 2. UI反馈
        self.log_label.configure(text="正在强力清理残留文件...", text_color="orange")
        self.stop_btn.configure(text="关闭中...", state="disabled")

        # 3. 强力文件清理逻辑
        if self.current_download_dir and os.path.exists(self.current_download_dir):
            try:
                # 获取目录下所有文件
                all_files = os.listdir(self.current_download_dir)
                for filename in all_files:
                    # >>>>>>> 核心修改：只要文件名包含 .tmp 就删除 <<<<<<<
                    # 这样可以匹配 "data.nc.tmp" 以及 "data.nc.tmp.9b46E0A3"
                    if ".tmp" in filename:
                        full_path = os.path.join(self.current_download_dir, filename)
                        try:
                            os.remove(full_path)
                            print(f"已清理碎片: {filename}")
                        except Exception as e:
                            print(f"清理 {filename} 失败: {e}")
            except Exception as e:
                print(f"扫描目录出错: {e}")

        # 4. 关闭网络
        if self.s3_client:
            try:
                self.s3_client._endpoint.http_session.close()
            except:
                pass

        # 5. 强制退出
        self.destroy()
        os._exit(0)

    def start_download(self):
        if self.is_downloading: return
        date_str = self.date_entry.get().strip()
        if len(date_str) != 6:
            messagebox.showerror("错误", "日期格式不正确")
            return

        self.is_downloading = True
        self.stop_requested = False
        self.total_bytes = 0
        self.last_bytes = 0

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
        with self.lock: curr = self.total_bytes
        diff = curr - self.last_bytes
        self.last_bytes = curr
        self.speed_label.configure(text=f"当前速度: {diff / 1048576:.2f} MB/s")
        self.after(1000, self.monitor_speed)

    def run_logic(self, date_str, max_workers):
        try:
            prefix = f"e5.oper.an.pl/{date_str}/"

            s3_config = Config(signature_version=UNSIGNED, max_pool_connections=max_workers + 5)
            self.s3_client = boto3.client('s3', config=s3_config)

            wanted_vars = self.get_selected_vars()
            self.log_label.configure(text=f"正在扫描... 目标变量: {wanted_vars if wanted_vars else '全部'}",
                                     text_color="#64b5f6")

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
                self.log_label.configure(text="未找到文件！", text_color="red")
                self.reset_ui()
                return

            target_dir = os.path.join(self.local_root, date_str)
            if not os.path.exists(target_dir): os.makedirs(target_dir)

            # 记录目录供清理使用
            self.current_download_dir = target_dir

            self.log_label.configure(text=f"发现 {len(files_to_download)} 个文件，准备下载...", text_color="white")

            slot_queue = queue.Queue()
            for i in range(max_workers):
                slot_queue.put(i)

            transfer_cfg = TransferConfig(use_threads=False)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for f_info in files_to_download:
                    if self.stop_requested: break
                    futures.append(executor.submit(
                        self.download_one, f_info, target_dir, transfer_cfg, slot_queue
                    ))
                for f in futures: f.result()

            if not self.stop_requested:
                self.log_label.configure(text="所有任务完成！", text_color="#00e676")
                messagebox.showinfo("成功", f"文件已保存至: {target_dir}")

        except Exception as e:
            self.log_label.configure(text=f"错误: {str(e)}", text_color="red")
            print(e)
        finally:
            self.reset_ui()

    def download_one(self, f_info, target_dir, cfg, slot_queue):
        if self.stop_requested: return

        sid = slot_queue.get()

        local_path = os.path.join(target_dir, f_info['Name'])
        # 临时文件：依然加上 .tmp 后缀
        # Boto3 会基于这个名字再加后缀，如 filename.nc.tmp.HASH
        temp_path = local_path + ".tmp"

        short_name = f_info['Name'][-25:]

        try:
            if self.stop_requested: return

            # --- 跳过检查 ---
            if os.path.exists(local_path):
                local_size = os.path.getsize(local_path)
                remote_size = f_info['Size']
                if local_size == remote_size:
                    self.update_slot(sid, f_info['Var'], short_name, 1.0, "已存在(跳过)")
                    return
                else:
                    self.update_slot(sid, f_info['Var'], short_name, 0, "不完整-重下")
            else:
                self.update_slot(sid, f_info['Var'], short_name, 0, "开始下载...")

            def cb(bytes_x):
                if self.stop_requested: return
                with self.lock:
                    self.total_bytes += bytes_x
                cb.done += bytes_x
                pct = cb.done / f_info['Size']
                t = time.time()
                if t - cb.last_t > 0.1 or pct >= 1.0:
                    self.update_slot(sid, f_info['Var'], short_name, pct)
                    cb.last_t = t

            cb.done = 0
            cb.last_t = 0

            # 关键：我们只管下载到 .tmp
            # 如果中途停止，文件名为 .tmp.HASH 或 .tmp
            # 清理函数会把只要带 .tmp 的全删了
            self.s3_client.download_file(self.bucket_name, f_info['Key'], temp_path, Config=cfg, Callback=cb)

            if not self.stop_requested:
                if os.path.exists(temp_path):
                    os.rename(temp_path, local_path)

        except Exception as e:
            if not self.stop_requested:
                self.update_slot(sid, "Err", "失败", 0, "错误")
        finally:
            slot_queue.put(sid)

    def update_slot(self, sid, var, name, pct, status=None):
        def _ui():
            txt = status if status else f"{int(pct * 100)}%"
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


if __name__ == "__main__":
    app = ERA5CleanStopApp()
    app.mainloop()