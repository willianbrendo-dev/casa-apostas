# Projeto Automacao Vision (Windows + Linux)

Este projeto usa Playwright + OpenCV para automacao visual com rotacao de proxy e logs detalhados.

## 1) Requisitos

- Python 3.11+ (recomendado)
- Internet para instalar dependencias
- Navegador Chromium/Chrome/Edge instalado (o script tenta detectar automaticamente)

## 2) Instalacao

No diretorio do projeto:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

No Windows (PowerShell):

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3) Navegador Playwright (fallback)

O script tenta abrir navegador do sistema primeiro. Se nao conseguir, usa navegador gerenciado pelo Playwright.

Se aparecer erro de executavel ausente, rode:

```bash
python -m playwright install chromium
```

No Linux, se faltar dependencia de sistema:

```bash
python -m playwright install --with-deps chromium
```

## 4) Configuracao

- Ajustar `TARGET_URL` em `prod_vision.py`
- Colocar proxies em `proxies.txt` (1 por linha), se desejar
- Garantir templates em `templates/`

## 5) Execucao

```bash
python prod_vision.py
```

## 6) Saida e logs

- Logs detalhados no terminal com timestamp, telefone, nivel e etapa
- Sucessos gravados em `sucessos_okslots.txt`

## 7) Observacoes de compatibilidade

- Linux: prioriza Chromium/Chrome local (inclui caminho snap do Ubuntu)
- Windows: tenta Chrome/Chromium/Edge local e fallback Playwright
- Se ambiente bloquear automacao, validar firewall, antivirus e politica de rede
