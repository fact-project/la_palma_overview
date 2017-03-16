import logging


def setup_logging(logfile=None, verbose=False):

    log = logging.getLogger()

    formatter = logging.Formatter(
        fmt='%(asctime)s|%(levelname)s|%(name)s|%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    log.addHandler(stream)

    if logfile is not None:
        filehandler = logging.FileHandler(logfile)
        filehandler.setFormatter(formatter)
        log.addHandler(filehandler)

    if verbose:
        logging.getLogger('la_palma_overview').setLevel(logging.DEBUG)
    else:
        logging.getLogger('la_palma_overview').setLevel(logging.INFO)
