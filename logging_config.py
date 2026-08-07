import logging


def configure_logging(level=logging.INFO):
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt)
    # reduce verbose logs from libraries
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
