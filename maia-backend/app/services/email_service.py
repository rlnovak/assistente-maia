from app.core.logging import get_logger

log = get_logger(__name__)


def send_magic_link(email: str, link: str) -> None:
    """Stub — Resend não configurado em dev. Loga o link para facilitar testes."""
    log.info("email_stub_magic_link", email=email, link=link)
