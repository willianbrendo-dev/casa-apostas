#!/usr/bin/env python3
"""
Formatador de proxies: limpa um arquivo bruto de proxies e produz o proxies.txt usado pelo bot.

Comportamento:
- Lê por padrão o arquivo 'ProxysBaixados.txt' na raiz do projeto (pode ser sobrescrito por argumento).
- Remove linhas vazias e prefixos numéricos (ex: "1: ").
- Aceita formatos comuns como:
  - ip:port:user:pass
  - http://user:pass@ip:port
  - user:pass@ip:port
- Garante que o arquivo de saída 'proxies.txt' contenha linhas no formato ip:port:user:pass, uma por linha.
- Ao final imprime: 'Faxina concluída! [X] proxies prontos para uso'
"""

import re
import sys
from urllib.parse import urlparse, unquote

INPUT_DEFAULT = "ProxysBaixados.txt"
OUTPUT_FILE = "proxies.txt"


def normalize_line(line):
    s = line.strip()
    if not s:
        return None

    # remove numbering prefixes like '1: ' or '1) '
    s = re.sub(r'^\s*\d+\s*[:\)\-]\s*', '', s)

    # remove surrounding quotes
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()

    # If it's a URL like http://user:pass@host:port
    if '://' in s:
        try:
            parsed = urlparse(s)
            username = parsed.username
            password = parsed.password
            hostname = parsed.hostname
            port = parsed.port
            if username and password and hostname and port:
                return f"{hostname}:{port}:{unquote(username)}:{unquote(password)}"
        except Exception:
            return None

    # If contains @ like user:pass@host:port
    if '@' in s:
        try:
            left, right = s.split('@', 1)
            # left -> user:pass
            if ':' not in left:
                return None
            user, pw = left.split(':', 1)
            # right -> host:port (may include path)
            right = right.split('/')[0]
            if ':' not in right:
                return None
            host, port = right.rsplit(':', 1)
            host = host.strip('[]')
            port = port.strip()
            if not port.isdigit():
                return None
            return f"{host}:{port}:{user}:{pw}"
        except Exception:
            return None

    # Otherwise expect ip:port:user:pass (4 parts)
    parts = [p.strip() for p in s.split(':')]
    if len(parts) == 4:
        host, port, user, pw = parts
        if port.isdigit():
            return f"{host}:{port}:{user}:{pw}"
        else:
            return None

    # fallback: try to extract last 3 tokens as port:user:pass and the rest as host
    if len(parts) > 4:
        # host may have colons (unlikely); take last three as port,user,pass
        port = parts[-3]
        user = parts[-2]
        pw = parts[-1]
        host = ':'.join(parts[:-3])
        if port.isdigit():
            return f"{host}:{port}:{user}:{pw}"

    return None


def main(argv=None):
    argv = argv or sys.argv[1:]
    infile = argv[0] if argv else INPUT_DEFAULT

    try:
        with open(infile, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()
    except FileNotFoundError:
        print(f"Arquivo de entrada não encontrado: {infile}")
        return 1

    cleaned = []
    for raw in raw_lines:
        line = raw.strip()
        if not line:
            continue
        ok = normalize_line(line)
        if ok:
            cleaned.append(ok)

    # deduplicate while preserving order
    seen = set()
    final = []
    for p in cleaned:
        if p not in seen:
            seen.add(p)
            final.append(p)

    # write to proxies.txt
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for p in final:
            f.write(p + '\n')

    print(f"Faxina concluída! [{len(final)}] proxies prontos para uso")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
