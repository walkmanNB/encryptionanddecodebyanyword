import base64
import os
import random
import string
import sys
import flet as ft
from datetime import datetime

# ==========================================
# 环境识别：区分 Windows 桌面与 Android 移动端
# ==========================================
IS_ANDROID = "android" in sys.platform.lower() or os.environ.get("ANDROID_ARGUMENT") is not None

if not IS_ANDROID:
    try:
        import tkinter as tk
        from tkinter import filedialog
        HAS_TKINTER = True
    except ImportError:
        HAS_TKINTER = False
else:
    HAS_TKINTER = False

# 安卓原生 Intent 支持（通过 pyjnius 调起 Android 系统文件管理器）
HAS_ANDROID_INTENT = False
if IS_ANDROID:
    try:
        from jnius import autoclass, cast
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Intent = autoclass('android.content.Intent')
        Uri = autoclass('android.net.Uri')
        HAS_ANDROID_INTENT = True
    except Exception:
        HAS_ANDROID_INTENT = False


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
        filename_bytes = original_filename.encode('utf-8')
        fn_len = len(filename_bytes)
        
        if fn_len > 65535:
            raise ValueError("文件名过长！")

        self._log(f"📝 准备加密：原名={original_filename}，数据={len(raw_bytes)} 字节")

        len_header = fn_len.to_bytes(2, byteorder='big')
        payload = len_header + filename_bytes + raw_bytes

        k_len = len(self.key_bytes)
        encrypted = bytearray(len(payload))
        state = sum(self.key_bytes) & 0xFF

        for i in range(len(payload)):
            k_byte = self.key_bytes[i % k_len]
            enc_byte = payload[i] ^ k_byte ^ state ^ ((i * 37) & 0xFF)
            encrypted[i] = enc_byte
            state = (state + enc_byte + k_byte) & 0xFF

        encoded_text = base64.b64encode(encrypted).decode('ascii')
        self._log(f"🔒 加密完成，密文字符数={len(encoded_text)}")
        return encoded_text

    def decrypt_and_unpack(self, encoded_text: str) -> tuple[bytes, str]:
        self._log(f"🔓 开始解密... 密文长度={len(encoded_text)} 字符")
        
        try:
            encrypted = base64.b64decode(encoded_text.encode('ascii'))
        except Exception as e:
            raise ValueError("Base64 解码失败，文本可能损毁或格式有误！") from e

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
            raise ValueError("数据损坏或非加密格式！")

        fn_len = int.from_bytes(payload[0:2], byteorder='big')

        if len(payload) < 2 + fn_len:
            raise ValueError("密钥错误或数据已被篡改！")

        filename_bytes = payload[2 : 2 + fn_len]
        raw_bytes = payload[2 + fn_len :]

        try:
            original_filename = filename_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError("密钥错误，无法还原文件名！") from e

        self._log(f"✅ 成功提取原文件名: [{original_filename}]")
        return raw_bytes, original_filename


# ==========================================
# 1. Windows 桌面专用原生对话框
# ==========================================
def tk_open_file(title="选择文件", filetypes=[("所有文件", "*.*")]):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    root.destroy()
    return path

def tk_save_file(title="保存文件", initialfile="", defaultextension=""):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.asksaveasfilename(title=title, initialfile=initialfile, defaultextension=defaultextension)
    root.destroy()
    return path


# ==========================================
# 2. Android 移动端原生系统文件选择器
# ==========================================
def android_open_file_dialog():
    """调起 Android 原生 SAF (Storage Access Framework) 打开文件窗口"""
    if not HAS_ANDROID_INTENT:
        return None
    try:
        intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.setType("*/*")
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        current_activity = PythonActivity.mActivity
        current_activity.startActivityForResult(Intent.createChooser(intent, "选择文件"), 1001)
    except Exception as e:
        print(f"Android Native Intent Error: {e}")
    return None


def main(page: ft.Page):
    page.title = "全隐蔽加解密工具"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 15
    page.scroll = ft.ScrollMode.AUTO

    key_input = ft.TextField(
        label="安全密钥（支持任意字符/中文/歌词）",
        password=True,
        can_reveal_password=True,
        expand=True
    )

    log_list = ft.ListView(expand=True, spacing=5, padding=10, auto_scroll=True)
    log_container = ft.Container(
        content=log_list,
        bgcolor=ft.Colors.BLACK12,
        border=ft.Border.all(1, ft.Colors.GREY_800),
        border_radius=8,
        height=200
    )

    # 路径手动/自动选择框（Android 端兼容兜底输入）
    path_input = ft.TextField(
        label="文件路径（Android端可直接粘贴或输入系统路径）",
        hint_text="/sdcard/Download/example.txt",
        visible=IS_ANDROID
    )

    def log(msg: str):
        time_str = datetime.now().strftime("%H:%M:%S")
        log_list.controls.append(
            ft.Text(f"[{time_str}] {msg}", size=12, font_family="Consolas", color=ft.Colors.GREEN_400)
        )
        page.update()

    def show_snack(text: str, is_error=False):
        snack = ft.SnackBar(
            content=ft.Text(text),
            bgcolor=ft.Colors.RED_700 if is_error else ft.Colors.GREEN_700
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # 触发加密
    def start_encrypt_action(e):
        key = key_input.value.strip()
        if not key:
            show_snack("请先填写密钥！", is_error=True)
            return

        input_path = ""
        save_path = ""

        if HAS_TKINTER:
            # 🖥️ Windows 原生文件窗口
            input_path = tk_open_file(title="选择要加密的文件")
            if not input_path:
                return
            
            rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            save_path = tk_save_file(
                title="选择加密文本保存位置",
                initialfile=f"enc_{rand_str}.txt",
                defaultextension=".txt"
            )
            if not save_path:
                return
        else:
            # 📱 Android 原生调用与路径逻辑
            if HAS_ANDROID_INTENT:
                android_open_file_dialog()

            input_path = path_input.value.strip()
            if not input_path or not os.path.exists(input_path):
                show_snack("请在上方文本框中输入或粘贴要加密的文件完整路径！", is_error=True)
                return
            
            rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            save_dir = os.path.dirname(input_path)
            save_path = os.path.join(save_dir, f"enc_{rand_str}.txt")

        # 执行加密核心计算
        cipher = CustomCompactCipher(key, logger=log)
        try:
            original_filename = os.path.basename(input_path)
            with open(input_path, 'rb') as f:
                raw_bytes = f.read()

            encoded_text = cipher.pack_and_encrypt(raw_bytes, original_filename)

            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(encoded_text)

            log(f"🎉 加密文件已保存到: {save_path}")
            show_snack("加密文件导出成功！")
        except Exception as err:
            log(f"❌ 加密失败: {str(err)}")
            show_snack(f"加密失败: {str(err)}", is_error=True)

    # 触发解密
    def start_decrypt_action(e):
        key = key_input.value.strip()
        if not key:
            show_snack("请先填写密钥！", is_error=True)
            return

        input_path = ""

        if HAS_TKINTER:
            # 🖥️ Windows 原生文件窗口
            input_path = tk_open_file(title="选择乱码加密文本", filetypes=[("TXT 文本", "*.txt"), ("所有文件", "*.*")])
            if not input_path:
                return
        else:
            # 📱 Android 原生调用
            if HAS_ANDROID_INTENT:
                android_open_file_dialog()

            input_path = path_input.value.strip()
            if not input_path or not os.path.exists(input_path):
                show_snack("请在上方文本框中输入或粘贴要解密的文件完整路径！", is_error=True)
                return

        cipher = CustomCompactCipher(key, logger=log)
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                encoded_text = f.read().strip()

            restored_bytes, original_filename = cipher.decrypt_and_unpack(encoded_text)

            if HAS_TKINTER:
                save_path = tk_save_file(
                    title=f"保存还原的文件 (提取原名: {original_filename})",
                    initialfile=original_filename
                )
            else:
                save_dir = os.path.dirname(input_path)
                save_path = os.path.join(save_dir, original_filename)

            if not save_path:
                return

            with open(save_path, 'wb') as f:
                f.write(restored_bytes)

            log(f"🎉 解密还原成功，文件已保存到: {save_path}")
            show_snack("文件已无损还原！")
        except Exception as err:
            log(f"❌ 解密失败: {str(err)}")
            show_snack("解密失败！密钥错误或文件不完整。", is_error=True)

    # 界面构建
    controls_list = [
        ft.Text("全隐蔽文件加解密工具", size=22, weight=ft.FontWeight.BOLD),
        ft.Text("藏入文件原名 | 输出混淆文本", size=12, color=ft.Colors.GREY_400),
        ft.Divider(),
        
        ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("1. 安全密钥设置", weight=ft.FontWeight.BOLD),
                    key_input
                ]),
                padding=15
            )
        )
    ]

    # 安卓环境下追加路径输入框
    if IS_ANDROID:
        controls_list.append(
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("2. 文件路径", weight=ft.FontWeight.BOLD),
                        path_input
                    ]),
                    padding=15
                )
            )
        )

    controls_list.extend([
        ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("3. 操作区域", weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.ElevatedButton(
                            "🔒 加密文件（隐藏原名）",
                            icon=ft.Icons.LOCK,
                            on_click=start_encrypt_action,
                            expand=True
                        ),
                        ft.ElevatedButton(
                            "🔓 解密文件（还原原名）",
                            icon=ft.Icons.LOCK_OPEN,
                            on_click=start_decrypt_action,
                            expand=True
                        )
                    ])
                ]),
                padding=15
            )
        ),
        
        ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("4. 运行日志", weight=ft.FontWeight.BOLD),
                    log_container
                ]),
                padding=15
            )
        )
    ])

    page.add(*controls_list)

    if HAS_TKINTER:
        env_name = "Windows 桌面原生引擎 (Tkinter)"
    elif HAS_ANDROID_INTENT:
        env_name = "Android 原生 Intent 引擎"
    else:
        env_name = "Android 路径模式"

    log(f"工具就绪。当前运行环境: [{env_name}]")


if __name__ == "__main__":
    ft.app(target=main)
