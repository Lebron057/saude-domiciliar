"""
Serviço de Precificação e Cálculos Financeiros — CuidaHome.
Responsável pelo cálculo de taxas da plataforma (take rate), diárias de plantões e repasses líquidos.
Todos os valores monetários são estritamente manipulados em centavos (INT UNSIGNED) para evitar erros de ponto flutuante.
"""

import os
from typing import Optional, Tuple

# Taxa padrão da plataforma (take rate de 12% a 15%)
DEFAULT_PLATFORM_FEE_PERCENT = 12.0

# Preços base de referência de mercado em centavos (caso a solicitação no mural não defina valor específico)
BASE_DIARIAS_12H = {
    "cuidador": 15000,            # R$ 150,00
    "tecnico_enfermagem": 20000,  # R$ 200,00
    "enfermeiro": 28000,          # R$ 280,00
}

BASE_DIARIAS_24H = {
    "cuidador": 28000,            # R$ 280,00
    "tecnico_enfermagem": 36000,  # R$ 360,00
    "enfermeiro": 50000,          # R$ 500,00
}


def get_platform_fee_percent() -> float:
    """Retorna o percentual de taxa configurado na variável de ambiente PLATFORM_FEE_PERCENT."""
    raw = os.getenv("PLATFORM_FEE_PERCENT", str(DEFAULT_PLATFORM_FEE_PERCENT))
    try:
        val = float(raw)
        return val if val >= 0 else DEFAULT_PLATFORM_FEE_PERCENT
    except ValueError:
        return DEFAULT_PLATFORM_FEE_PERCENT


def calculate_plantao_pricing(
    valor_diaria_centavos: int,
    fee_percent: Optional[float] = None,
) -> Tuple[int, int, float]:
    """
    Calcula o split financeiro de um plantão:
      - valor_diaria_centavos: total pago pela família.
      - taxa_centavos: fatia da plataforma (take rate).
      - repasse_centavos: valor líquido a ser transferido ao profissional.

    Garante invariante: taxa_centavos + repasse_centavos == valor_diaria_centavos.

    Retorna:
      (taxa_centavos, repasse_centavos, fee_percent_aplicado)
    """
    if valor_diaria_centavos <= 0:
        raise ValueError("O valor da diária deve ser estritamente positivo (> 0).")

    percent = fee_percent if fee_percent is not None else get_platform_fee_percent()
    if percent < 0 or percent > 100:
        raise ValueError("O percentual de taxa deve estar entre 0% e 100%.")

    # Arredondamento exato para o centavo mais próximo
    taxa_centavos = int(round(valor_diaria_centavos * (percent / 100.0)))
    repasse_centavos = valor_diaria_centavos - taxa_centavos

    return taxa_centavos, repasse_centavos, percent


def format_centavos_brl(centavos: int) -> str:
    """Formata valor em centavos para moeda BRL legível (ex: 15000 -> 'R$ 150,00')."""
    reais = centavos / 100.0
    formatted = f"{reais:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"
