# YouTube para MP3

Aplicativo desktop para Windows que baixa áudio de links informados pelo usuário e o converte para MP3.

## Executável

O executável independente está em [`FELIPECOMMEDO/release/YouTubeMP3.exe`](FELIPECOMMEDO/release/YouTubeMP3.exe). Ele é armazenado com Git LFS; instale o Git LFS para cloná-lo ou baixá-lo.

O programa abre uma interface gráfica. Selecione um arquivo `.txt` com um link por linha e escolha a pasta de destino. O executável inclui yt-dlp, FFmpeg e ffprobe.

## Gerar novamente no Windows

1. Instale Python e Git LFS.
2. Coloque `ffmpeg.exe` e `ffprobe.exe` ao lado de `youtube_mp3_gui.py`.
3. Crie o ambiente e instale os pacotes:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install yt-dlp pyinstaller
   ```

4. Execute `exe.bat`. O arquivo será gerado em `dist\YouTubeMP3.exe`.

Use apenas links cujo download você tenha autorização para fazer e respeite os termos de serviço aplicáveis.
