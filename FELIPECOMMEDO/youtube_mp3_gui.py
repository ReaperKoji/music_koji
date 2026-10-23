import os
import sys
import shutil
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import yt_dlp
from yt_dlp.utils import DownloadCancelled, match_filter_func


def pasta_base():
    """Pasta onde o .exe (ou o script) está."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def achar_ffmpeg():
    """Retorna (ok, pasta_dos_binarios).
    Ordem: embutido dentro do .exe, ao lado do programa, PATH do sistema."""
    candidatas = []
    if getattr(sys, "_MEIPASS", None):  # ffmpeg empacotado dentro do .exe
        candidatas.append(sys._MEIPASS)
    candidatas.append(pasta_base())
    for pasta in candidatas:
        ffmpeg_path = os.path.join(pasta, "ffmpeg.exe")
        ffprobe_path = os.path.join(pasta, "ffprobe.exe")
        if os.path.isfile(ffmpeg_path) and os.path.isfile(ffprobe_path):
            return True, pasta
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    if ffmpeg_path and ffprobe_path:
        if os.path.dirname(ffmpeg_path).casefold() == os.path.dirname(ffprobe_path).casefold():
            return True, os.path.dirname(ffmpeg_path)
        return True, ffmpeg_path
    return False, None


def ler_links(caminho):
    """Lê o txt: um link por linha. Linhas vazias e que começam com # são ignoradas."""
    links = []
    with open(caminho, "r", encoding="utf-8-sig") as f:
        for linha in f:
            linha = linha.strip()
            if linha and not linha.startswith("#"):
                links.append(linha)
    return links


class LogYT:
    """Redireciona as mensagens do yt-dlp para a janela."""

    def __init__(self, enviar):
        self.enviar = enviar

    def debug(self, msg):
        if not msg.startswith("[debug] "):
            self.info(msg)

    def info(self, msg):
        self.enviar(msg)

    def warning(self, msg):
        pass

    def error(self, msg):
        self.enviar("ERRO: " + msg)


class App:
    def __init__(self, root):
        self.root = root
        root.title("YouTube para MP3")
        root.geometry("720x520")
        root.minsize(620, 420)

        self.fila = queue.Queue()
        self.parar = threading.Event()
        self.thread = None

        padrao_txt = os.path.join(pasta_base(), "links.txt")
        self.var_txt = tk.StringVar(value=padrao_txt if os.path.exists(padrao_txt) else "")
        self.var_saida = tk.StringVar(value=os.path.join(pasta_base(), "musicas"))
        self.var_min = tk.StringVar(value="3")

        frm = ttk.Frame(root, padding=12)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(4, weight=1)

        ttk.Label(frm, text="Arquivo .txt com os links:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.var_txt).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(frm, text="Escolher...", command=self.escolher_txt).grid(row=0, column=2)

        ttk.Label(frm, text="Pasta de destino:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.var_saida).grid(row=1, column=1, sticky="ew", padx=6)
        ttk.Button(frm, text="Escolher...", command=self.escolher_saida).grid(row=1, column=2)

        ttk.Label(frm, text="Duração mínima (minutos):").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Spinbox(frm, from_=0, to=60, increment=0.5, width=6,
                    textvariable=self.var_min).grid(row=2, column=1, sticky="w", padx=6)

        botoes = ttk.Frame(frm)
        botoes.grid(row=3, column=0, columnspan=3, sticky="w", pady=8)
        self.btn_iniciar = ttk.Button(botoes, text="Iniciar download", command=self.iniciar)
        self.btn_iniciar.pack(side="left")
        self.btn_parar = ttk.Button(botoes, text="Parar", command=self.cancelar, state="disabled")
        self.btn_parar.pack(side="left", padx=8)

        caixa = ttk.Frame(frm)
        caixa.grid(row=4, column=0, columnspan=3, sticky="nsew")
        caixa.columnconfigure(0, weight=1)
        caixa.rowconfigure(0, weight=1)
        self.txt_log = tk.Text(caixa, state="disabled", wrap="word", height=10)
        self.txt_log.grid(row=0, column=0, sticky="nsew")
        barra = ttk.Scrollbar(caixa, command=self.txt_log.yview)
        barra.grid(row=0, column=1, sticky="ns")
        self.txt_log.configure(yscrollcommand=barra.set)

        self.progresso = ttk.Progressbar(frm, maximum=100)
        self.progresso.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 0))

        self.var_status = tk.StringVar(value="Pronto.")
        ttk.Label(frm, textvariable=self.var_status).grid(row=6, column=0, columnspan=3, sticky="w")

        self.root.after(100, self.processar_fila)

    # ---------- interface ----------
    def escolher_txt(self):
        c = filedialog.askopenfilename(filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
        if c:
            self.var_txt.set(c)

    def escolher_saida(self):
        c = filedialog.askdirectory()
        if c:
            self.var_saida.set(c)

    def log(self, msg):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def processar_fila(self):
        try:
            while True:
                tipo, valor = self.fila.get_nowait()
                if tipo == "log":
                    self.log(valor)
                elif tipo == "prog":
                    self.progresso["value"] = valor
                elif tipo == "status":
                    self.var_status.set(valor)
                elif tipo == "fim":
                    self.btn_iniciar.configure(state="normal")
                    self.btn_parar.configure(state="disabled")
                    self.progresso["value"] = 0
        except queue.Empty:
            pass
        self.root.after(100, self.processar_fila)

    # ---------- ações ----------
    def iniciar(self):
        arquivo = self.var_txt.get().strip()
        saida = self.var_saida.get().strip()

        if not arquivo or not os.path.exists(arquivo):
            messagebox.showerror("Erro", "Escolha o arquivo .txt com os links.")
            return
        try:
            minutos = float(self.var_min.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Erro", "Duração mínima inválida.")
            return
        ok, ffmpeg_dir = achar_ffmpeg()
        if not ok:
            messagebox.showerror(
                "ffmpeg não encontrado",
                "Coloque o ffmpeg.exe e o ffprobe.exe na mesma pasta deste programa.",
            )
            return
        try:
            links = ler_links(arquivo)
        except Exception as e:
            messagebox.showerror("Erro", f"Não consegui ler o arquivo:\n{e}")
            return
        if not links:
            messagebox.showerror("Erro", "O arquivo não tem nenhum link.")
            return

        os.makedirs(saida, exist_ok=True)
        self.parar.clear()
        self.btn_iniciar.configure(state="disabled")
        self.btn_parar.configure(state="normal")
        self.log(f"{len(links)} link(s) encontrados. Duração mínima: {minutos:g} min.")

        self.thread = threading.Thread(
            target=self.trabalho,
            args=(links, saida, int(minutos * 60), ffmpeg_dir),
            daemon=True,
        )
        self.thread.start()

    def iniciar_auto(self):
        """Ao abrir o programa: se houver um links.txt ao lado do .exe, já começa."""
        if self.var_txt.get() and os.path.exists(self.var_txt.get()):
            self.log("links.txt encontrado. Iniciando automaticamente...")
            self.iniciar()
        else:
            self.log("Coloque um arquivo links.txt na mesma pasta deste programa "
                     "(ou escolha um arquivo acima) e clique em Iniciar download.")

    def cancelar(self):
        self.parar.set()
        self.var_status.set("Cancelando...")

    # ---------- download (thread separada) ----------
    def enviar(self, tipo, valor):
        self.fila.put((tipo, valor))

    def hook(self, d):
        if self.parar.is_set():
            raise DownloadCancelled("Cancelado pelo usuário")
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                self.enviar("prog", d["downloaded_bytes"] * 100 / total)
            nome = os.path.basename(d.get("filename", ""))
            self.enviar("status", f"Baixando: {nome}")
        elif d["status"] == "finished":
            self.enviar("prog", 100)
            self.enviar("status", "Convertendo para MP3...")

    def trabalho(self, links, saida, segundos_min, ffmpeg_dir):
        opcoes = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(saida, "%(playlist_title|Avulsas)s", "%(title)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            # só baixa vídeos com duração igual ou maior que o mínimo
            "match_filter": match_filter_func(f"duration >= {segundos_min}"),
            # não baixa de novo o que já foi baixado antes
            "download_archive": os.path.join(saida, "baixadas.txt"),
            "ignoreerrors": True,
            "noprogress": True,
            "quiet": True,
            "no_warnings": True,
            "logger": LogYT(lambda m: self.enviar("log", m)),
            "progress_hooks": [self.hook],
        }
        if ffmpeg_dir:
            opcoes["ffmpeg_location"] = ffmpeg_dir

        try:
            with yt_dlp.YoutubeDL(opcoes) as ydl:
                for i, link in enumerate(links, 1):
                    if self.parar.is_set():
                        break
                    self.enviar("log", f"\n=== Link {i}/{len(links)}: {link} ===")
                    try:
                        ydl.download([link])
                    except DownloadCancelled:
                        break
                    except Exception as e:
                        self.enviar("log", f"ERRO neste link: {e}")
        except Exception as e:
            self.enviar("log", f"ERRO: {e}")

        if self.parar.is_set():
            self.enviar("log", "\nDownload cancelado.")
            self.enviar("status", "Cancelado.")
        else:
            self.enviar("log", "\nConcluído!")
            self.enviar("status", "Concluído.")
        self.enviar("fim", None)


def main():
    root = tk.Tk()
    app = App(root)
    root.after(500, app.iniciar_auto)
    root.mainloop()


if __name__ == "__main__":
    main()