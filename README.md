# Clipster

Aplicativo desktop simples, com interface gráfica em Tkinter, para baixar vídeos e áudios a partir de uma URL (YouTube e outros sites suportados pelo [yt-dlp](https://github.com/yt-dlp/yt-dlp)).

## Funcionalidades

- Buscar informações do vídeo a partir de uma URL
- Baixar em **vídeo (MP4)** ou **áudio (MP3)**
- Escolher a qualidade (resolução do vídeo ou bitrate do áudio)
- Escolher a pasta de destino do download
- Barra de progresso durante o download
- Interface em tema escuro

## Requisitos

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/) instalado e disponível no PATH do sistema (necessário para exportar em MP3 e para mesclar vídeo+áudio em algumas qualidades)

## Instalação

```bash
pip install -r requirements.txt
```

## Como usar

```bash
python main.py
```

1. Cole a URL do vídeo e clique em **Buscar**
2. Escolha o modo (Vídeo ou Áudio) e a qualidade desejada
3. Escolha a pasta onde o arquivo será salvo
4. Clique em **Baixar**

## Gerar executável (Windows)

Para gerar um `.exe` standalone (não requer Python instalado):

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name Clipster main.py
```

O executável será criado em `dist/Clipster.exe`.

## Aviso

Use este aplicativo apenas para baixar conteúdo que você tem o direito de baixar (vídeos próprios, de domínio público ou com licença/autorização explícita). Respeite os termos de uso das plataformas e os direitos autorais dos criadores de conteúdo.

## Tecnologias

- [Python](https://www.python.org/)
- [Tkinter](https://docs.python.org/3/library/tkinter.html)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [sv-ttk](https://github.com/rdbende/Sun-Valley-ttk-theme) (tema escuro)
