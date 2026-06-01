import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("edge-mock")


def print_banner():
    logger.info("edge-mock \u2014 microservice mock environment")


def print_violation(service: str, method: str, path: str, detail: str):
    logger.warning("[VIOLATION] %s %s %s: %s", service, method, path, detail)


def print_service_table(services: list[dict]):
    logger.info("services:")
    for s in services:
        logger.info("  %s :%s %s (%s)", s["name"], s["port"], s["path"], s["type"])