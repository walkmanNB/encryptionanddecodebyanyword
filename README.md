# encryptionanddecodebyanyword
加密任何文件用任何文字！
# 🛡️ Custom Compact Cipher (全隐蔽反直觉字节加密工具)

> **"Everything is Bytes. Beyond Traditional Encryption."**  
> 万物皆可字节。打破传统加密逻辑，将文件名、格式元数据与原始数据打包流混淆，实现彻底的“反直觉”隐蔽防护。

---

## ✨ 核心特性 (Features)

- **🎭 全隐蔽文件名隐藏 (Full Metadata Camouflage)**
  - 原始文件名（包含中文、空格及扩展名如 `.mp3`, `.docx`, `.png`）在加密前被作为二进制元数据打包封装进密文中。
  - 导出文件自动重命名为无意义的随机字符（如 `enc_a8F9kQ2L.txt`），外部审查完全无法通过文件名或后缀判断原始数据类型与规模。

- **🎵 歌词口令与高熵保护 (Passphrase / Lyrics Key Support)**
  - 原生支持中文歌词、诗词或任意长文本作为解密密钥。
  - **心理学隐写**：你可以将密钥写在公开的动态或签名中，旁观者只会以为是日常情感抒发，而自动化字典暴破工具对此类长句子完全失效。

- **📦 零冗余体积控制 (Minimal Overhead)**
  - 摒弃了传统加密格式复杂的权限头与文件校验码，仅保留 2 字节元数据头。
  - 基于 Base64 / 自定义字符集混淆，密文膨胀率严格控制在 **~33%** 极限水平（例如 3MB 音频加密后约为 4MB 文本）。

- **⚡ 字节级流混淆 (Byte-Level Stream XOR & Dynamic State Transformation)**
  - 底层基于动态状态演变（Dynamic State Evolution）与位置字节异或算法，不依赖外部重型加密库，纯 Python/C 原生实现。

---

## 💡 为什么是“反直觉”？ (The Anti-Intuition Paradigm)

| 传统加密 (Traditional Encryption) | 本工具 (Custom Compact Cipher) |
| :--- | :--- |
| 保留扩展名或明确标记为 `.enc` / `.zip` | 强制输出为毫无特征的纯文本乱码 `.txt` |
| 文件名清晰暴露（如 `2026财务报表.xlsx`） | 文件名彻底藏进密文，外部仅看到随机乱码字符串 |
| 需记忆高难度随机字符密码 | 一句脑海里的歌词（如“*刮风这天试过握着你手*”）即可作为物理钥匙 |
| 区分“文本加密”与“文件加密” | **万物皆可字节**：一句歌词与一首 10MB 的 MP3 在底层处理逻辑上完全等价 |

---

## 🛠️ 快速上手 (Quick Start)

### 1. 运行桌面 GUI 客户端 (Windows)

确保已安装 Python 3.8+，运行主程序：

```bash
python test.py
