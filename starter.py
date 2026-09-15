"""Ponto de entrada do protótipo Gerir Android.

Este protótipo é destinado apenas a aparelhos da empresa que tenham sido
inscritos e autorizados. As acções de controlo são simuladas até existir uma
integração MDM/suporte remoto aprovada.
"""

import os

from app import create_app


app = create_app()


if __name__ == "__main__":
    # A porta 80 é o padrão pedido para implantação atrás de um IP/domínio.
    # Em produção, coloque a aplicação atrás de um proxy HTTPS.
    port = int(os.environ.get("PORT", "80"))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
