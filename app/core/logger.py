import logging
import warnings


def configure_logging() -> None:
    logging_fmt = "[%(asctime)s][%(levelname)s][%(name)s]: %(message)s"
    logging.basicConfig(level=logging.INFO, format=logging_fmt)
    warnings.filterwarnings(action="ignore")
