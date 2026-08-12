import base64
import os
import random
import string
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

class CustomCompactCipher:
    """核心自定义加密/解密逻辑"""
    def __init__(self, key: str, logger=None):
        self.key_bytes = key.encode('utf-8')
        self.logger = logger
        if not self.key_bytes:
            raise ValueError("密钥不能为空！")

    def _log(self, msg: str):
        if self.logger:
            self.logger(msg)

    def pack_and_encrypt(self, raw_bytes: bytes, original_filename: str) -> str:
        """
        将 [完整原始文件名] 和 [文件二进制数据] 打包加密
        数据结构：[文件名UTF-8字节长度(2字节)] + [文件名UTF-8字节] + [文件二进制内容]
        """
        filename_bytes = original_filename.encode('utf-8')
        fn_len = len(filename_bytes)
        
        if fn_len > 65535:
            raise ValueError("文件名过长！")

        self._log(f"📝 准备加密：文件原名={original_filename}，数据大小={len(raw_bytes)} 字节")

        # 1. 打包元数据（2字节表示文件名长度 + 文件名 + 原始数据）
        len_header = fn_len.to_bytes(2, byteorder='big')
        payload = len_header + filename_bytes + raw_bytes
        self._log(f"📦 元数据已封装，总 Payload 大小={len(payload)} 字节")

        # 2. 核心动态异或与状态混淆
        k_len = len(self.key_bytes)
        encrypted = bytearray(len(payload))
        state = sum(self.key_bytes) & 0xFF

        for i in range(len(payload)):
            k_byte = self.key_bytes[i % k_len]
            enc_byte = payload[i] ^ k_byte ^ state ^ ((i * 37) & 0xFF)
            encrypted[i] = enc_byte
            # 状态演变绑定在密文字节上
            state = (state + enc_byte + k_byte) & 0xFF

        encoded_text = base64.b64encode(encrypted).decode('ascii')
        self._log(f"🔒 加密完成，生成文本字符数={len(encoded_text)}")
        return encoded_text

    def decrypt_and_unpack(self, encoded_text: str) -> tuple[bytes, str]:
        """解密并自动提取解析出原始数据与完整文件名"""
        self._log(f"🔓 开始解密... 读取文本长度={len(encoded_text)} 字符")
        
        try:
            encrypted = base64.b64decode(encoded_text.encode('ascii'))
        except Exception as e:
            raise ValueError("Base64 解码失败，文本可能损毁或非合法加密文本！") from e

        # 1. 还原混淆
        k_len = len(self.key_bytes)
        payload = bytearray(len(encrypted))
        state = sum(self.key_bytes) & 0xFF

        for i in range(len(encrypted)):
            k_byte = self.key_bytes[i % k_len]
            enc_byte = encrypted[i]
            dec_byte = enc_byte ^ k_byte ^ state ^ ((i * 37) & 0xFF)
            payload[i] = dec_byte
            state = (state + enc_byte + k_byte) & 0xFF

        payload = bytes(payload)

        if len(payload) < 2:
            raise ValueError("数据严重损坏或非加密格式！")

        # 2. 解析 2 字节的文件名长度
        fn_len = int.from_bytes(payload[0:2], byteorder='big')
        self._log(f"🔍 解析元数据：检测到隐藏的文件名长度={fn_len} 字节")

        if len(payload) < 2 + fn_len:
            raise ValueError("密钥错误或数据被篡改，无法解密出原始文件名！")

        # 3. 提取文件名与真实数据
        filename_bytes = payload[2 : 2 + fn_len]
        raw_bytes = payload[2 + fn_len :]

        try:
            original_filename = filename_bytes.decode('utf-8')
        except Exception as e:
            self._log("❌ 文件名解码失败，密钥不匹配！")
            raise ValueError("密钥错误，无法还原文件名！") from e

        self._log(f"✅ 隐藏文件名还原成功: [{original_filename}]，数据大小={len(raw_bytes)} 字节")
        return raw_bytes, original_filename


class CipherApp(tk.Tk):
    """GUI 界面逻辑"""
    def __init__(self):
        super().__init__()
        self.title("全隐蔽文件加解密工具（隐藏文件名/自动随机重命名）")
        self.geometry("640x560")
        self.resizable(False, False)
        
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 密钥区域
        key_frame = ttk.LabelFrame(main_frame, text=" 1. 安全密钥设置（支持任意字符/中文） ", padding="10")
        key_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(key_frame, text="密钥:").pack(side=tk.LEFT, padx=(0, 10))
        self.key_entry = ttk.Entry(key_frame, show="*", width=40)
        self.key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.show_key_var = tk.BooleanVar(value=False)
        show_cb = ttk.Checkbutton(key_frame, text="显示", variable=self.show_key_var, command=self._toggle_key_visibility)
        show_cb.pack(side=tk.LEFT, padx=(10, 0))

        # 2. 操作按钮
        action_frame = ttk.LabelFrame(main_frame, text=" 2. 全隐蔽文件加解密 ", padding="10")
        action_frame.pack(fill=tk.X, pady=(0, 10))

        btn_grid = ttk.Frame(action_frame)
        btn_grid.pack(expand=True)

        encrypt_btn = ttk.Button(btn_grid, text="🔒 加密文件（隐藏原名输出乱码 TXT）", command=self.encrypt_action, width=32)
        encrypt_btn.grid(row=0, column=0, padx=10, pady=5, ipady=5)

        decrypt_btn = ttk.Button(btn_grid, text="🔓 解密 TXT（自动读取并还原文件名）", command=self.decrypt_action, width=32)
        decrypt_btn.grid(row=0, column=1, padx=10, pady=5, ipady=5)

        # 3. Log 运行日志控制台
        log_frame = ttk.LabelFrame(main_frame, text=" 3. 运行日志 (Log) ", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.log_text = tk.Text(log_frame, height=12, state=tk.DISABLED, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 9))
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        self.log("工具就绪。原文件名将被自动隐藏打包进加密内容中。")

    def log(self, message: str):
        self.log_text.config(state=tk.NORMAL)
        time_str = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{time_str}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _toggle_key_visibility(self):
        if self.show_key_var.get():
            self.key_entry.config(show="")
        else:
            self.key_entry.config(show="*")

    def _get_cipher(self):
        key = self.key_entry.get()
        if not key:
            messagebox.showwarning("密钥缺失", "请输入加密/解密密钥！")
            return None
        return CustomCompactCipher(key, logger=self.log)

    def encrypt_action(self):
        cipher = self._get_cipher()
        if not cipher:
            return

        input_path = filedialog.askopenfilename(title="选择要加密的文件", filetypes=[("所有文件", "*.*")])
        if not input_path:
            return

        # 提取真正的原文件名（例如 "我的秘密歌单.mp3"）
        original_filename = os.path.basename(input_path)

        # 自动生成随机乱码文件名作为导出的 TXT 文件名（如 "X9k_aL3q.txt"）
        rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        random_txt_name = f"enc_{rand_str}.txt"

        output_path = filedialog.asksaveasfilename(
            title="选择加密 TXT 保存位置（文件名已自动替换为随机字符串）",
            defaultextension=".txt",
            initialfile=random_txt_name,
            filetypes=[("TXT 文本", "*.txt")]
        )
        if not output_path:
            return

        try:
            with open(input_path, 'rb') as f:
                raw_bytes = f.read()

            encoded_text = cipher.pack_and_encrypt(raw_bytes, original_filename)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(encoded_text)

            self.log(f"🎉 文件已加密！真实名称 [{original_filename}] 已隐藏入密文中")
            self.log(f"📁 输出混淆 txt: {os.path.basename(output_path)}")
            messagebox.showinfo("加密成功", f"加密完成！\n原文件名 [{original_filename}] 已成功藏入密文中。")
        except Exception as e:
            self.log(f"❌ 加密失败: {str(e)}")
            messagebox.showerror("加密失败", str(e))

    def decrypt_action(self):
        cipher = self._get_cipher()
        if not cipher:
            return

        input_path = filedialog.askopenfilename(title="选择乱码 TXT 加密文件", filetypes=[("TXT 文本", "*.txt"), ("所有文件", "*.*")])
        if not input_path:
            return

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                encoded_text = f.read().strip()

            restored_bytes, original_filename = cipher.decrypt_and_unpack(encoded_text)

            # 自动把保存弹窗中的文件名设置为最初解析出的【真实原文件名】
            output_path = filedialog.asksaveasfilename(
                title=f"检测到藏在密文里的原文件名: [{original_filename}]，选择还原位置",
                initialfile=original_filename,
                filetypes=[("原始文件类型", f"*{os.path.splitext(original_filename)[1]}"), ("所有文件", "*.*")]
            )
            if not output_path:
                return

            with open(output_path, 'wb') as f:
                f.write(restored_bytes)

            self.log(f"🎉 文件无损还原成功！保存为: {output_path}")
            messagebox.showinfo("解密成功", f"成功还原！\n已自动提取文件原名：\n{original_filename}")
        except Exception as e:
            self.log(f"❌ 解密失败: {str(e)}")
            messagebox.showerror("解密失败", f"解密失败！密钥错误或文件不完整。")


if __name__ == "__main__":
    app = CipherApp()
    app.mainloop()