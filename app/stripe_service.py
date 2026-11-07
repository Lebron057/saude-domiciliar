"""
Módulo de Integração com a Stripe (Modo de Teste) - Atividade 7.
Gerencia a criação de Checkout Sessions e a validação de assinaturas de Webhooks.
Nenhuma informação de cartão de crédito passa ou é armazenada pela nossa aplicação.
"""

import os
from typing import Optional
import stripe

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
stripe.api_key = STRIPE_API_KEY


def is_stripe_configured() -> bool:
    """Verifica se a chave de API do Stripe está configurada."""
    return bool(STRIPE_API_KEY and not STRIPE_API_KEY.startswith("sk_test_placeholder"))


def create_premium_checkout_session(
    usuario_id: int,
    user_email: str,
    user_nome: str,
    base_url: str,
) -> stripe.checkout.Session:
    """
    Cria uma Checkout Session no Stripe (Modo de Teste) para assinatura do Plano Premium.
    Redireciona para o checkout hospedado pelo Stripe.
    """
    if not is_stripe_configured():
        raise ValueError("Stripe API Key não configurada. Defina STRIPE_API_KEY no arquivo .env.")

    stripe.api_key = STRIPE_API_KEY

    # Monta URLs de retorno
    success_url = f"{base_url.rstrip('/')}/catalog?premium_success=true"
    cancel_url = f"{base_url.rstrip('/')}/profile/{usuario_id}?canceled=true"

    session_params = {
        "payment_method_types": ["card"],
        "mode": "subscription",
        "line_items": [
            {
                "price_data": {
                    "currency": "brl",
                    "product_data": {
                        "name": "Locação de Equipamentos — CuidaHome",
                        "description": "Assinatura mensal recorrente para locação ortopédica/hospitalar.",
                    },
                    "unit_amount": 1990,  # R$ 19,90 / mês
                    "recurring": {
                        "interval": "month",
                    },
                },
                "quantity": 1,
            }
        ],
        "client_reference_id": str(usuario_id),
        "metadata": {
            "usuario_id": str(usuario_id),
            "user_nome": user_nome,
        },
        "success_url": success_url,
        "cancel_url": cancel_url,
    }

    # Apenas repassa customer_email pré-preenchido se tiver formato válido com TLD (.com, etc.)
    # Caso contrário, o Stripe Checkout permite ao cliente preencher o e-mail de faturamento com segurança
    if user_email and "@" in user_email and "." in user_email.split("@")[-1]:
        session_params["customer_email"] = user_email

    session = stripe.checkout.Session.create(**session_params)
    return session


def create_plantao_checkout_session(
    plantao_id: int,
    valor_diaria_centavos: int,
    user_email: str,
    base_url: str,
) -> stripe.checkout.Session:
    """
    Cria uma Checkout Session no Stripe (modo payment / pontual) para pagamento da diária de plantão.
    Metadados incluem tipo='plantao' e plantao_id para roteamento no webhook assíncrono.
    """
    if not is_stripe_configured():
        raise ValueError("Stripe API Key não configurada. Defina STRIPE_API_KEY no arquivo .env.")

    stripe.api_key = STRIPE_API_KEY

    success_url = f"{base_url.rstrip('/')}/painel/familia?plantao_pago=true&plantao_id={plantao_id}"
    cancel_url = f"{base_url.rstrip('/')}/painel/familia?canceled=true&plantao_id={plantao_id}"

    session_params = {
        "payment_method_types": ["card"],
        "mode": "payment",
        "line_items": [
            {
                "price_data": {
                    "currency": "brl",
                    "product_data": {
                        "name": f"Plantão de Saúde Domiciliar #{plantao_id}",
                        "description": "Pagamento de diária e taxa de intermediação de cuidados domiciliares — CuidaHome.",
                    },
                    "unit_amount": valor_diaria_centavos,
                },
                "quantity": 1,
            }
        ],
        "client_reference_id": str(plantao_id),
        "metadata": {
            "tipo": "plantao",
            "plantao_id": str(plantao_id),
        },
        "success_url": success_url,
        "cancel_url": cancel_url,
    }

    if user_email and "@" in user_email and "." in user_email.split("@")[-1]:
        session_params["customer_email"] = user_email

    session = stripe.checkout.Session.create(**session_params)
    return session


def create_subscription_checkout_session(
    locacao_id: int,
    stripe_price_id: str,
    cliente_id: int,
    user_email: str,
    base_url: str,
) -> stripe.checkout.Session:
    """
    Cria uma Checkout Session no Stripe em mode='subscription' para locação mensal de equipamento.
    Configura metadados para ativação da locação e provisionamento da caução via Webhook.
    """
    if not is_stripe_configured():
        raise ValueError("Stripe API Key não configurada. Defina STRIPE_API_KEY no arquivo .env.")

    stripe.api_key = STRIPE_API_KEY

    success_url = f"{base_url.rstrip('/')}/painel/familia?locacao_sucesso=true&locacao_id={locacao_id}"
    cancel_url = f"{base_url.rstrip('/')}/equipamentos?locacao_cancelada=true&locacao_id={locacao_id}"

    session_params = {
        "payment_method_types": ["card"],
        "mode": "subscription",
        "line_items": [
            {
                "price": stripe_price_id,
                "quantity": 1,
            }
        ],
        "client_reference_id": str(cliente_id),
        "metadata": {
            "tipo": "locacao",
            "locacao_id": str(locacao_id),
            "cliente_id": str(cliente_id),
        },
        "subscription_data": {
            "metadata": {
                "tipo": "locacao",
                "locacao_id": str(locacao_id),
            }
        },
        "success_url": success_url,
        "cancel_url": cancel_url,
    }

    if user_email and "@" in user_email and "." in user_email.split("@")[-1]:
        session_params["customer_email"] = user_email

    session = stripe.checkout.Session.create(**session_params)
    return session


def criar_autorizacao_caucao(
    locacao_id: int,
    valor_caucao_centavos: int,
    customer_id: str,
    payment_method_id: Optional[str] = None,
) -> Optional[stripe.PaymentIntent]:
    """
    Cria uma pré-autorização de garantia/caução no cartão com capture_method='manual' (Opção A).
    Não debita fundos imediatamente; apenas reserva o limite de garantia.
    """
    if not is_stripe_configured():
        return None

    stripe.api_key = STRIPE_API_KEY

    params = {
        "amount": valor_caucao_centavos,
        "currency": "brl",
        "customer": customer_id,
        "capture_method": "manual",
        "metadata": {
            "tipo": "caucao",
            "locacao_id": str(locacao_id),
        },
    }

    if payment_method_id:
        params["payment_method"] = payment_method_id
        params["confirm"] = True
        params["off_session"] = True

    try:
        return stripe.PaymentIntent.create(**params)
    except Exception as e:
        print(f"[Stripe] Aviso ao autorizar caução da locacao_id={locacao_id}: {e}")
        return None


def cancelar_autorizacao_caucao(payment_intent_id: str) -> bool:
    """
    Cancela a autorização de caução (hold), liberando o saldo do cliente sem qualquer cobrança.
    """
    if not is_stripe_configured() or not payment_intent_id or payment_intent_id.startswith("pi_caucao_loc_"):
        return True

    stripe.api_key = STRIPE_API_KEY
    try:
        stripe.PaymentIntent.cancel(payment_intent_id)
        return True
    except Exception as e:
        print(f"[Stripe] Aviso ao cancelar autorização {payment_intent_id}: {e}")
        return False


def cancelar_assinatura_locacao(subscription_id: str, cancel_at_period_end: bool = True) -> bool:
    """
    Encerra a renovação automática da assinatura mensal da locação.
    """
    if not is_stripe_configured() or not subscription_id:
        return True

    stripe.api_key = STRIPE_API_KEY
    try:
        stripe.Subscription.modify(subscription_id, cancel_at_period_end=cancel_at_period_end)
        return True
    except Exception as e:
        print(f"[Stripe] Aviso ao encerrar assinatura {subscription_id}: {e}")
        return False


def verify_and_construct_webhook_event(
    payload: bytes,
    sig_header: str,
) -> stripe.Event:
    """
    Valida a assinatura criptográfica do Webhook da Stripe usando o Webhook Secret.
    Garante que requisições forjadas ou sem assinatura sejam prontamente rejeitadas.
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret or webhook_secret.startswith("whsec_placeholder"):
        raise ValueError("STRIPE_WEBHOOK_SECRET não configurado.")

    stripe.api_key = STRIPE_API_KEY
    return stripe.Webhook.construct_event(
        payload=payload,
        sig_header=sig_header,
        secret=webhook_secret,
    )
