import logging

from xninetzy.os.security.pii_filter import install_pii_filter


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    install_pii_filter(logging.getLogger())
