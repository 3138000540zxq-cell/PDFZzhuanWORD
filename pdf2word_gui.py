import logging
import os
import sys
import tempfile
import traceback
import threading
import queue
from pathlib import Path
from tkinter import Tk, Toplevel, filedialog, messagebox, StringVar
from tkinter import ttk

from pdf2docx import Converter


APP_NAME = "PDF转Word启动器"


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def ensure_app_dirs() -> tuple[Path, Path, Path]:
    base_dir = app_base_dir()
    logs_dir = base_dir / "logs"
    outputs_dir = base_dir / "outputs"

    logs_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    return base_dir, logs_dir, outputs_dir


def configure_logging(logs_dir: Path) -> Path:
    log_path = logs_dir / "conversion.log"
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
        force=True,
    )
    return log_path


def unique_docx_path(output_dir: Path, pdf_path: Path) -> Path:
    docx_path = output_dir / f"{pdf_path.stem}.docx"
    if not docx_path.exists():
        return docx_path

    index = 1
    while True:
        candidate = output_dir / f"{pdf_path.stem}_{index}.docx"
        if not candidate.exists():
            return candidate
        index += 1


def convert_pdf_to_docx(pdf_path: Path, output_dir: Path) -> Path:
    docx_path = unique_docx_path(output_dir, pdf_path)

    logging.info("Converting PDF: %s", pdf_path)
    logging.info("Output DOCX: %s", docx_path)

    converter = Converter(str(pdf_path))
    try:
        converter.convert(str(docx_path))
    finally:
        converter.close()

    return docx_path




def show_progress_window(root: Tk, total: int):
    """Show a small progress window with file name, progress bar, and status."""
    win = Toplevel(root)
    win.title(f"{APP_NAME} - \u8f6c\u6362\u4e2d")
    win.resizable(False, False)
    win.attributes("-topmost", True)

    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    w, h = 420, 140
    left = (sw - w) // 2
    top = (sh - h) // 2
    win.geometry(f"{w}x{h}+{left}+{top}")

    file_var = StringVar(win, "\u51c6\u5907\u5c31\u7eea\u2026")
    ttk.Label(win, textvariable=file_var, wraplength=390, anchor="center").pack(pady=(18, 6))

    progress = ttk.Progressbar(win, mode="determinate", length=380)
    progress.pack(pady=4)

    status_var = StringVar(win, "")
    ttk.Label(win, textvariable=status_var, foreground="#666").pack(pady=4)

    win.update()
    return win, progress, file_var, status_var


def run_self_test() -> int:
    base_dir, logs_dir, outputs_dir = ensure_app_dirs()
    log_path = configure_logging(logs_dir)
    logging.info("Self-test started. base=%s outputs=%s", base_dir, outputs_dir)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        sample_pdf = temp_path / "self_test.pdf"

        import fitz

        document = fitz.open()
        page = document.new_page()
        page.insert_text((72, 72), "PDF to Word self test")
        document.save(sample_pdf)
        document.close()

        docx_path = convert_pdf_to_docx(sample_pdf, temp_path)
        passed = log_path.exists() and outputs_dir.exists() and docx_path.exists()

    logging.info("Self-test %s.", "passed" if passed else "failed")
    return 0 if passed else 1


def main() -> int:
    _, logs_dir, outputs_dir = ensure_app_dirs()
    log_path = configure_logging(logs_dir)

    root = Tk()
    root.withdraw()

    pdf_files = filedialog.askopenfilenames(
        title="请选择需要转换的 PDF 文件，可以多选",
        filetypes=[
            ("PDF 文件", "*.pdf"),
            ("所有文件", "*.*"),
        ],
    )

    if not pdf_files:
        messagebox.showinfo("提示", "你没有选择任何 PDF 文件。")
        root.destroy()
        return 0

    total = len(pdf_files)
    progress_win, progress, file_var, status_var = show_progress_window(root, total)

    result_queue = queue.Queue()
    success_files: list[Path] = []
    failed_files: list[tuple[Path, str]] = []

    # Background worker: runs all conversions in a separate thread
    def worker():
        for i, file in enumerate(pdf_files):
            pdf_path = Path(file)
            result_queue.put(('progress', i, pdf_path.name))
            try:
                docx_path = convert_pdf_to_docx(pdf_path, outputs_dir)
                result_queue.put(('success', pdf_path, docx_path))
                logging.info('[%d/%d] OK: %s', i + 1, total, pdf_path.name)
            except Exception as exc:
                result_queue.put(('failure', pdf_path, str(exc)))
                logging.error('[%d/%d] FAILED: %s  %s', i + 1, total, pdf_path.name, exc)
                logging.error(traceback.format_exc())
        result_queue.put(('finished',))

    threading.Thread(target=worker, daemon=True).start()

    def poll_queue():
        try:
            while True:
                msg = result_queue.get_nowait()
                kind = msg[0]
                if kind == 'progress':
                    _, i, name = msg
                    file_var.set(name)
                    status_var.set(f'正在转换 {i + 1}/{total} …')
                    progress['value'] = (i / total) * 100 if total > 1 else 0
                elif kind == 'success':
                    _, pdf_path, docx_path = msg
                    success_files.append(docx_path)
                elif kind == 'failure':
                    _, pdf_path, exc = msg
                    failed_files.append((pdf_path, exc))
                elif kind == 'finished':
                    progress_win.destroy()
                    msg_text = (
                        '\u8f6c\u6362\u5b8c\u6210\u3002\n\n'
                        f'\u6210\u529f\uff1a{len(success_files)} \u4e2a\n'
                        f'\u5931\u8d25\uff1a{len(failed_files)} \u4e2a\n\n'
                        f'\u9ed8\u8ba4\u8f93\u51fa\u4f4d\u7f6e\uff1a{outputs_dir}'
                    )
                    if failed_files:
                        msg_text += f'\n\n\u5931\u8d25\u8be6\u60c5\u5df2\u5199\u5165\u65e5\u5fd7\uff1a{log_path}\n\n\u5931\u8d25\u6587\u4ef6\uff1a'
                        for pdf_path, _ in failed_files:
                            msg_text += f'\n{pdf_path.name}'
                    messagebox.showinfo('PDF 转 Word', msg_text)
                    try:
                        os.startfile(outputs_dir)
                    except Exception:
                        logging.warning('Could not open output directory: %s', outputs_dir)
                    root.destroy()
                    return
        except queue.Empty:
            pass
        root.after(150, poll_queue)

    poll_queue()
    root.mainloop()
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(run_self_test())

    raise SystemExit(main())
