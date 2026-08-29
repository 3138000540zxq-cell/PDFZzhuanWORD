# PDF 转 Word 启动器

一个面向 Windows 的简易桌面工具，可批量选择 PDF 文件并转换为 Word（DOCX）文档。界面使用 Tkinter，转换功能由 `pdf2docx` 提供。

## 功能

- 一次选择并转换多个 PDF 文件
- 转换过程在后台线程运行，界面保持响应
- 显示文件名、进度和完成状态
- 自动避免覆盖同名 DOCX 文件
- 将转换结果保存到 `outputs` 目录
- 将运行日志保存到 `logs/conversion.log`

## 本地运行

建议使用 Python 3.10 或更高版本。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python .\pdf2word_gui.py
```

## 自测

```powershell
python .\pdf2word_gui.py --self-test
```

自测会临时生成一个 PDF，并验证它能否成功转换为 DOCX。

## 构建 Windows 程序

在 PowerShell 中运行：

```powershell
.\build_onedir.ps1
```

脚本会创建独立构建环境、安装依赖，并将打包结果写入 `dist` 目录。

## 隐私说明

PDF 转换完全在本机执行。`outputs`、`logs`、虚拟环境及打包产物已加入 `.gitignore`，不会提交到 Git 仓库。

