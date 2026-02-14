# API 参考文档

## 目录

1. [主程序类](#主程序类)
2. [配置管理](#配置管理)
3. [下载方法](#下载方法)
4. [工具函数](#工具函数)
5. [异常类](#异常类)

---

## 主程序类

### ERA5ResumeDownloadApp

主应用程序类，继承自 CustomTkinter。

#### 初始化

```python
app = ERA5ResumeDownloadApp()
app.mainloop()
```

#### 主要属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `bucket_name` | str | S3 存储桶名称 (`nsf-ncar-era5`) |
| `s3_client` | boto3.client | S3 客户端实例 |
| `is_downloading` | bool | 是否正在下载 |
| `stop_requested` | bool | 是否请求停止 |
| `max_workers` | int | 最大并发线程数 (1-10) |
| `max_retries` | int | 最大重试次数 (默认 6) |

---

## 配置管理

### ERA5_VARS

ERA5 变量字典，定义所有可下载的气象变量。

```python
ERA5_VARS = {
    "动力与热力学": {
        "t": "空气温度 (K)",
        "u": "U风分量 (m/s)",
        "v": "V风分量 (m/s)",
        "w": "垂直速度 (Pa/s)",
        "z": "位势高度",
        "d": "散度",
        "vo": "相对涡度",
        "pv": "位涡"
    },
    "湿度与云物理": {
        "q": "比湿",
        "r": "相对湿度",
        "cc": "云量",
        "ciwc": "云冰水含量",
        "clwc": "云液态水含量",
        "crwc": "雨水含量",
        "cswc": "雪水含量"
    },
    "化学成分": {
        "o3": "臭氧"
    }
}
```

**用法示例**:
```python
# 获取所有变量代码
all_vars = []
for category in ERA5_VARS.values():
    all_vars.extend(category.keys())

# 获取特定类别的变量
thermal_vars = ERA5_VARS["动力与热力学"]
```

---

## 下载方法

### download_one_with_resume()

支持断点续传的单文件下载方法。

**签名**:
```python
def download_one_with_resume(
    self,
    f_info: dict,           # 文件信息字典
    target_dir: str,         # 目标目录
    cfg: TransferConfig,      # 传输配置
    slot_queue: queue.Queue  # 线程槽队列
) -> None
```

**参数**:
- `f_info`: 包含 `Key`, `Size`, `Var`, `Name` 的字典
- `target_dir`: 保存目录路径
- `cfg`: Boto3 传输配置对象
- `slot_queue`: 线程槽队列，用于并发控制

**异常**:
- `DownloadStoppedException`: 用户停止下载
- `FileIncompleteException`: 文件下载不完整

**示例**:
```python
file_info = {
    'Key': 'e5.oper.an.pl/202510/.../t.nc',
    'Size': 104857600,
    'Var': 't',
    'Name': 'e5.oper.an.pl.202510.00_06.t.nc'
}
app.download_one_with_resume(file_info, './data', cfg, queue)
```

---

### _download_with_retry()

带重试机制的内部下载方法。

**签名**:
```python
def _download_with_retry(
    self,
    f_info: dict,
    temp_path: str,         # 临时文件路径
    start_byte: int,        # 起始字节位置
    sid: int               # 线程槽 ID
) -> None
```

**重试策略**:
- 最大重试次数: 6 次
- 退避算法: 指数退避 (2^n 秒)
- 重试延迟: 2s → 4s → 8s → 16s → 32s → 64s

**Range 请求**:
```http
Range: bytes=102400-  # 从 100KB 开始续传
```

---

## 工具函数

### save_config()

保存当前配置到文件。

**签名**:
```python
def save_config(self) -> None
```

**保存内容**:
```json
{
  "date": "202510",
  "local_root": "./era5_data",
  "thread_count": 5,
  "selected_vars": ["t", "u", "v", "q"]
}
```

**配置文件**: `.era5_gui_config.json`

---

### load_config()

从文件加载配置。

**签名**:
```python
def load_config(self) -> None
```

**恢复内容**:
- 日期设置
- 保存路径
- 线程数量
- 变量选择

---

### save_progress() / load_progress()

进度管理方法。

**save_progress**:
```python
def save_progress(self, progress_data: dict) -> None
```

**load_progress**:
```python
def load_progress(self, target_dir: str) -> dict | None
```

**进度数据结构**:
```json
{
  "completed": [
    "e5.oper.an.pl.202510.00_06.t.nc",
    "e5.oper.an.pl.202510.00_06.u.nc"
  ],
  "date": "2025-02-14 20:30:15"
}
```

**进度文件**: `.era5_download_progress.json`

---

### update_slot()

更新下载槽的 UI 显示。

**签名**:
```python
def update_slot(
    self,
    sid: int,           # 槽位 ID (0-9)
    var: str,           # 变量代码
    name: str,          # 文件名（短）
    pct: float,         # 进度 (0.0-1.0)
    status: str = None   # 状态文本
) -> None
```

**示例**:
```python
# 更新进度
app.update_slot(0, 't', '...temperature.nc', 0.65, '65%')

# 更新状态
app.update_slot(1, 'u', '...wind_u.nc', 0.0, '网络错误')
```

---

## 异常类

### DownloadStoppedException

用户主动停止下载时抛出。

```python
try:
    app.download_one_with_resume(...)
except DownloadStoppedException:
    print("下载被用户停止")
```

---

### FileIncompleteException

文件下载不完整时抛出。

```python
try:
    app._download_with_retry(...)
except FileIncompleteException as e:
    print(f"文件不完整: {e}")
    # 记录到失败列表
```

---

## 扩展开发

### 添加新变量

编辑 `ERA5_VARS` 字典：

```python
ERA5_VARS = {
    ...
    "自定义变量": {
        "custom_var": "自定义变量描述"
    }
}
```

### 自定义重试策略

修改 `max_retries` 和 `retry_delay`:

```python
self.max_retries = 10      # 增加重试次数
self.retry_delay = 5         # 增加初始延迟
```

### 添加进度回调

```python
def on_progress(pct, speed, eta):
    print(f"进度: {pct}%, 速度: {speed} MB/s")

# 在下载循环中调用
on_progress(pct, speed, eta)
```

---

## 数据结构

### 文件信息字典 (f_info)

```python
{
    'Key': str,      # S3 对象键
    'Size': int,     # 文件大小（字节）
    'Var': str,      # 变量代码
    'Name': str       # 文件名
}
```

### 失败信息字典

```python
{
    'name': str,      # 文件名
    'error': str,     # 错误消息
    'size': int,      # 已下载大小
    'expected': int    # 期望大小
}
```

---

## 最佳实践

### 1. 错误处理

```python
try:
    app.run_logic(date_str, max_workers)
except ClientError as e:
    logger.error(f"S3 错误: {e}")
except ConnectionError as e:
    logger.error(f"连接错误: {e}")
except Exception as e:
    logger.error(f"未知错误: {e}")
```

### 2. 资源清理

```python
finally:
    if app.s3_client:
        app.s3_client._endpoint.http_session.close()
```

### 3. 进度监控

```python
# 定期检查进度
if file_count % 10 == 0:
    elapsed = time.time() - start_time
    speed = (file_count * 60) / elapsed
    print(f"速度: {speed:.2f} 文件/分钟")
```

---

**版本**: 3.1.0
**更新日期**: 2025-02-14
