"""Leitura, validação e agregações do snapshot de tráfego de rede."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

COLUNAS_OBRIGATORIAS = {
    "session_id", "timestamp", "user_id", "user_name", "department",
    "user_ip", "mac_address", "device_type", "dest_domain", "dest_ip",
    "dest_port", "protocol", "category", "bytes_sent", "bytes_received",
    "total_bytes", "total_megabytes", "packets_sent", "packets_received",
    "total_packets", "duration_seconds", "threat_risk", "action",
}
COLUNAS_NUMERICAS = [
    "dest_port", "bytes_sent", "bytes_received", "total_bytes",
    "total_megabytes", "packets_sent", "packets_received",
    "total_packets", "duration_seconds",
]
COLUNAS_TEXTO = sorted(COLUNAS_OBRIGATORIAS - set(COLUNAS_NUMERICAS) - {"timestamp"})


def ler_dados(origem: str | Path | bytes | BinaryIO) -> pd.DataFrame:
    """Carrega CSV UTF-8 ou UTF-8-BOM e não altera a planilha original.

    Os volumes de gráficos são recalculados usando total_bytes / 1.048.576,
    evitando acumular os arredondamentos de total_megabytes por linha.
    """
    if isinstance(origem, bytes):
        origem = BytesIO(origem)
    tabela = pd.read_csv(origem, encoding="utf-8-sig", dtype={c: "string" for c in COLUNAS_TEXTO})
    tabela.columns = tabela.columns.str.strip().str.removeprefix("\ufeff")
    faltantes = sorted(COLUNAS_OBRIGATORIAS - set(tabela.columns))
    if faltantes:
        raise ValueError("Colunas obrigatórias ausentes no CSV: " + ", ".join(faltantes))
    if tabela.empty:
        raise ValueError("O arquivo CSV não contém registros de tráfego.")
    for coluna in COLUNAS_NUMERICAS:
        tabela[coluna] = pd.to_numeric(tabela[coluna], errors="coerce")
    if tabela[COLUNAS_NUMERICAS].isna().any().any():
        cols = tabela[COLUNAS_NUMERICAS].columns[tabela[COLUNAS_NUMERICAS].isna().any()].tolist()
        raise ValueError("Campos numéricos inválidos ou vazios: " + ", ".join(cols))
    tabela["timestamp"] = pd.to_datetime(tabela["timestamp"], errors="coerce")
    if tabela["timestamp"].isna().any():
        raise ValueError("Há valores inválidos na coluna timestamp; use AAAA-MM-DD HH:MM:SS.")
    if tabela[COLUNAS_TEXTO].isna().any().any():
        raise ValueError("Existem campos de identificação/classificação vazios no CSV.")
    if (tabela[["bytes_sent", "bytes_received", "total_bytes"]] < 0).any().any():
        raise ValueError("Há volumes de bytes negativos no CSV.")
    if not (tabela["bytes_sent"] + tabela["bytes_received"] == tabela["total_bytes"]).all():
        raise ValueError("Há registros em que total_bytes difere da soma de upload e download.")
    tabela["volume_mb"] = tabela["total_bytes"] / (1024 ** 2)
    tabela["hora"] = tabela["timestamp"].dt.hour
    tabela["data"] = tabela["timestamp"].dt.date
    return tabela.sort_values("timestamp").reset_index(drop=True)


def filtrar_dados(
    tabela: pd.DataFrame,
    *,
    departamentos: list[str] | None = None,
    usuarios: list[str] | None = None,
    categorias: list[str] | None = None,
    acoes: list[str] | None = None,
    riscos: list[str] | None = None,
    protocolos: list[str] | None = None,
    datas: list | None = None,
    horas: tuple[int, int] | None = None,
) -> pd.DataFrame:
    resultado = tabela
    for nome, selecionados in (
        ("department", departamentos), ("user_name", usuarios),
        ("category", categorias), ("action", acoes),
        ("threat_risk", riscos), ("protocol", protocolos), ("data", datas),
    ):
        if selecionados:
            resultado = resultado[resultado[nome].isin(selecionados)]
    if horas is not None:
        inicio, fim = horas
        resultado = resultado[resultado["hora"].between(inicio, fim)]
    return resultado.copy()


def indicadores(tabela: pd.DataFrame) -> dict:
    total = len(tabela)
    bloqueados = int(tabela["action"].eq("BLOCKED").sum())
    alto = int(tabela["threat_risk"].eq("Alto").sum())
    incidentes = int((tabela["action"].eq("BLOCKED") | tabela["threat_risk"].eq("Alto")).sum())
    return {
        "sessoes": total,
        "usuarios": int(tabela["user_id"].nunique()),
        "departamentos": int(tabela["department"].nunique()),
        "volume_mb": float(tabela["volume_mb"].sum()),
        "upload_mb": float(tabela["bytes_sent"].sum() / 1024**2),
        "download_mb": float(tabela["bytes_received"].sum() / 1024**2),
        "bloqueados": bloqueados,
        "alto": alto,
        "alertas": int(tabela["action"].eq("ALERT").sum()),
        "incidentes": incidentes,
        "taxa_bloqueio": bloqueados / total * 100 if total else 0.0,
    }


def top_usuarios(tabela: pd.DataFrame, limite: int = 10) -> pd.DataFrame:
    return (tabela.groupby(["user_name", "department"], as_index=False)
            .agg(volume_mb=("volume_mb", "sum"), conexoes=("session_id", "count"))
            .sort_values("volume_mb", ascending=False).head(limite).reset_index(drop=True))


def por_departamento(tabela: pd.DataFrame) -> pd.DataFrame:
    return (tabela.groupby("department", as_index=False)
            .agg(volume_mb=("volume_mb", "sum"), conexoes=("session_id", "count"))
            .sort_values("volume_mb", ascending=False))


def top_destinos(tabela: pd.DataFrame, limite: int = 10) -> pd.DataFrame:
    return (tabela.groupby(["dest_domain", "category"], as_index=False)
            .agg(conexoes=("session_id", "count"), volume_mb=("volume_mb", "sum"))
            .sort_values(["conexoes", "volume_mb"], ascending=False)
            .head(limite).reset_index(drop=True))


def por_categoria(tabela: pd.DataFrame, limite: int = 10) -> pd.DataFrame:
    return (tabela.groupby("category", as_index=False)
            .agg(volume_mb=("volume_mb", "sum"), conexoes=("session_id", "count"))
            .sort_values("volume_mb", ascending=False).head(limite))


def obter_incidentes(tabela: pd.DataFrame, foco: str = "Bloqueados ou risco alto") -> pd.DataFrame:
    if foco == "Somente bloqueados":
        mascara = tabela["action"].eq("BLOCKED")
    elif foco == "Somente risco alto":
        mascara = tabela["threat_risk"].eq("Alto")
    elif foco == "Somente alertas":
        mascara = tabela["action"].eq("ALERT")
    else:
        mascara = tabela["action"].eq("BLOCKED") | tabela["threat_risk"].eq("Alto")
    return tabela.loc[mascara].sort_values("timestamp", ascending=False).reset_index(drop=True)
