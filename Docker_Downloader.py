import os
import json
import requests
import tkinter as tk
from tkinter import messagebox, scrolledtext
from threading import Thread

# 禁用不安全请求警告
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

apiversion = "v2"
final_list_of_blobs = []

class BlobDownloaderApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Docker Registry Blob Downloader")
        self.center_window()  # 调用居中方法

        # 输入框和按钮放在一行
        self.url_label = tk.Label(master, text="URL:")
        self.url_label.grid(row=0, column=0, padx=5, pady=5)

        self.url_entry = tk.Entry(master, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5)

        self.select_button = tk.Button(master, text="选择仓库和标签", command=self.select_repository)
        self.select_button.grid(row=0, column=2, padx=5, pady=5)

        self.log_text = scrolledtext.ScrolledText(master, width=80, height=10)
        self.log_text.grid(row=1, column=0, columnspan=3, padx=5, pady=5)

    def center_window(self):
        window_width = self.master.winfo_reqwidth()
        window_height = self.master.winfo_reqheight()

        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()

        x = int((screen_width / 2) - (window_width / 2))
        y = int((screen_height / 2) - (window_height / 2))

        self.master.geometry(f'+{x}+{y}')  # 设置窗口位置

    def select_repository(self):
        url = self.url_entry.get().strip()
        if not url:
            # messagebox.showerror("Error", "请先输入 Docker Registry API v2 的 URL 地址。")
            self.log_text.insert(tk.END, "请先输入 Docker Registry API v2 的 URL 地址。\n")
            return

        try:
            list_of_repos = self.list_repos(url)
            repo_selection = tk.StringVar(self.master)
            repo_selection.set(list_of_repos[0] if list_of_repos else "")

            frame = tk.Frame(self.master)
            frame.grid(row=2, column=0, columnspan=3, sticky='w')

            repo_label = tk.Label(frame, text="选择仓库:")
            repo_label.pack(side='left', padx=1, pady=1)

            repo_dropdown = tk.OptionMenu(frame, repo_selection, *list_of_repos)
            repo_dropdown.pack(side='left', padx=1, pady=1)

            tag_selection = tk.StringVar(self.master)
            tag_label = tk.Label(frame, text="选择标签:")
            tag_label.pack(side='left', padx=1, pady=1)

            tag_dropdown = tk.OptionMenu(frame, tag_selection, "")
            tag_dropdown.pack(side='left', padx=1, pady=1)

            def update_tags_dropdown(*args):
                selected_repo = repo_selection.get()
                tags = self.find_tags(url, selected_repo)
                tag_selection.set(tags[0] if tags else "")
                menu = tag_dropdown['menu']
                menu.delete(0, 'end')
                for tag in tags:
                    menu.add_command(label=tag, command=tk._setit(tag_selection, tag))

            repo_selection.trace('w', update_tags_dropdown)
            update_tags_dropdown()

            download_button = tk.Button(self.master, text="下载", command=lambda: self.start_download(url, repo_selection.get(), tag_selection.get()), width=10)
            download_button.grid(row=2, column=2, columnspan=3, padx=5, pady=10)

        except Exception as e:
            self.log_text.insert(tk.END, "Error", f"发生错误: {str(e)}\n")
            # messagebox.showerror("Error", f"发生错误: {str(e)}")

    def list_repos(self, url):
        req = requests.get(f"{url}/{apiversion}/_catalog", verify=False)
        return json.loads(req.text)["repositories"]

    def find_tags(self, url, reponame):
        req = requests.get(f"{url}/{apiversion}/{reponame}/tags/list", verify=False)
        data = json.loads(req.content)
        if "tags" in data:
            return data["tags"]
        return []

    def list_blobs(self, url, reponame, tag):
        req = requests.get(f"{url}/{apiversion}/{reponame}/manifests/{tag}", verify=False)
        data = json.loads(req.content)
        if "fsLayers" in data:
            for x in data["fsLayers"]:
                curr_blob = x['blobSum'].split(":")[1]
                if curr_blob not in final_list_of_blobs:
                    final_list_of_blobs.append(curr_blob)

    def start_download(self, url, reponame, tag):
        self.log_text.delete(1.0, tk.END)  # 清空日志框
        self.log_text.insert(tk.END, f"选择的仓库: {reponame}\n选择的标签: {tag}\n\n")
        download_thread = Thread(target=self.download_blobs, args=(url, reponame, tag))
        download_thread.start()

    def download_blobs(self, url, reponame, tag):
        try:
            self.log_text.insert(tk.END, "开始下载,请稍后...\n")
            self.list_blobs(url, reponame, tag)
            current_dir = os.getcwd()
            target_dir = os.path.join(current_dir, f"{reponame}_{tag.replace(':', '_')}")
            os.makedirs(target_dir, exist_ok=True)
            for blob in final_list_of_blobs:
                self.download_blob(url, reponame, blob, target_dir)
            self.log_text.insert(tk.END, f"全部下载完成。目标文件夹: {target_dir}\n")
        except Exception as e:
            self.log_text.insert(tk.END, f"下载失败: {str(e)}\n")

    def download_blob(self, url, reponame, blobdigest, dirname):
        req = requests.get(f"{url}/{apiversion}/{reponame}/blobs/sha256:{blobdigest}", verify=False)
        filename = f"{blobdigest}.tar.gz"
        with open(os.path.join(dirname, filename), 'wb') as f:
            f.write(req.content)

def main():
    root = tk.Tk()
    app = BlobDownloaderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
