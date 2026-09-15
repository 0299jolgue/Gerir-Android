# Gerir Android — protótipo

Painel web de demonstração para administrar **apenas dispositivos Android empresariais inscritos e autorizados**. Inclui login, dashboard, lista de dispositivos, página de controlo simulada e preparação de agente APK.

## Arranque

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
python starter.py
```

O processo escuta em `0.0.0.0:80` por padrão. Para desenvolvimento sem privilégios, use `PORT=8080 python starter.py`. Aceda a `http://IP-DO-SERVIDOR/`.

Credenciais iniciais: `admin` / `admin123`. Em qualquer implantação real, defina `ADMIN_USERNAME`, `ADMIN_PASSWORD` e `SECRET_KEY` no ambiente antes do primeiro arranque, e coloque a aplicação atrás de HTTPS.

## Estado do protótipo

Os quatro dispositivos iniciais, o streaming de ecrã e os comandos são dados de demonstração guardados em SQLite. O sistema **não** captura ecrãs, lê notificações nem controla dispositivos reais.

Para produção, integre Android Management API para inscrição/políticas, Firebase Cloud Messaging para comunicação e uma solução de suporte remoto empresarial que apresente consentimento. Registe cada ação e só permita dispositivos da organização.
