---
name: arxiv-downloader
description: 如何从 arXiv 下载论文 LaTeX 源码。Agent 在收到论文链接后使用此技能。
---

# arXiv 论文下载技能

## 下载步骤

### 1. 提取论文 ID

从用户输入中提取 arXiv ID，支持格式：
- `https://arxiv.org/abs/2603.03251` → `2603.03251`
- `https://arxiv.org/pdf/2603.03251` → `2603.03251`
- `2603.03251` → `2603.03251`
- `arXiv:2603.03251` → `2603.03251`

### 2. 创建工作目录

```bash
mkdir -p papers/{arxiv_id}/source
```

### 3. 下载源码

**根据系统环境选择可用的下载工具（参考 system prompt 中的系统环境信息）：**

curl（macOS/Linux 通常自带）：
```bash
curl -L "https://arxiv.org/e-print/{arxiv_id}" -o papers/{arxiv_id}/source.tar.gz
```

wget（如果可用）：
```bash
wget "https://arxiv.org/e-print/{arxiv_id}" -O papers/{arxiv_id}/source.tar.gz
```

### 4. 解压

```bash
cd papers/{arxiv_id} && tar -xzf source.tar.gz -C source/
```

如果 tar 失败（可能是单个 gzip 文件），尝试：
```bash
cd papers/{arxiv_id} && gunzip -c source.tar.gz > source/main.tex
```

### 5. 验证

```bash
ls papers/{arxiv_id}/source/
```

确认有 `.tex` 文件存在。

## 错误处理

- **网络错误**: 重试 2-3 次
- **无源码**: 部分论文无 LaTeX 源码，告知用户
- **格式异常**: 尝试多种解压方式 (tar.gz / gz / zip)
