"""Relatório imprimível de um evento selecionado na tabela."""
from __future__ import annotations

from html import escape


def gerar_relatorio_html(registro: dict) -> str:
    campos = [
        ("Sessão", "session_id"), ("Data e hora", "timestamp"),
        ("Usuário", "user_name"), ("ID do usuário", "user_id"),
        ("Departamento", "department"), ("Equipamento", "device_type"),
        ("IP de origem", "user_ip"), ("MAC", "mac_address"),
        ("Domínio de destino", "dest_domain"), ("IP de destino", "dest_ip"),
        ("Porta", "dest_port"), ("Protocolo", "protocol"),
        ("Categoria", "category"), ("Risco atribuído", "threat_risk"),
        ("Ação registrada", "action"), ("Bytes enviados", "bytes_sent"),
        ("Bytes recebidos", "bytes_received"), ("Total de bytes", "total_bytes"),
        ("Pacotes", "total_packets"),
    ]
    if str(registro.get("action")) == "BLOCKED":
        interpretacao = "A fonte registrou a ação BLOCKED para esta sessão. O registro, isoladamente, não comprova ataque ou comprometimento."
    elif str(registro.get("threat_risk")) == "Alto":
        interpretacao = "A fonte classificou a conexão como risco alto; recomenda-se avaliação contextual pela equipe responsável."
    else:
        interpretacao = "A fonte registrou um alerta. A classificação exige validação no contexto da política de segurança."
    linhas = "\n".join(
        f"<tr><th>{escape(rotulo)}</th><td>{escape(str(registro.get(chave, '—')))}</td></tr>"
        for rotulo, chave in campos
    )
    titulo = escape(str(registro.get("session_id", "Evento")))
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatório de evento - {titulo}</title>
<style>body{{font-family:Arial,sans-serif;max-width:880px;margin:36px auto;padding:0 18px;color:#15243b}}
h1{{color:#133e60}}p{{line-height:1.55}}table{{width:100%;border-collapse:collapse;margin:20px 0}}
th,td{{padding:10px;border-bottom:1px solid #dfe5ef;text-align:left;word-break:break-word}}
th{{background:#f1f6fc;width:35%}}.nota{{padding:14px;background:#eef7ff;border-left:4px solid #27a4de}}
footer{{font-size:12px;color:#6c7886;margin-top:28px}}@media print{{body{{margin:0}}}}</style></head>
<body><h1>Relatório de evento de rede</h1><p><strong>Identificador:</strong> {titulo}</p>
<p class="nota">{escape(interpretacao)}</p><table>{linhas}</table>
<footer>Gerado a partir de um snapshot CSV do exercício. Não constitui diagnóstico forense nem monitoramento em tempo real. Abra no navegador e use Ctrl+P para imprimir ou salvar em PDF.</footer>
</body></html>"""
