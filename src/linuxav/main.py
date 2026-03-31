import sys
import logging
import logging.config
from pathlib import Path
import argparse


def setup_logging(verbose: bool = False):
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    config_path = Path(__file__).parent.parent.parent / "config" / "logging.yaml"
    
    if config_path.exists():
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
            config["handlers"]["file"]["filename"] = str(logs_dir / "linuxav.log")
            logging.config.dictConfig(config)
    else:
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


def parse_args():
    parser = argparse.ArgumentParser(description="LinuxAV Antivirus")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger("linuxav")
    logger.info("LinuxAV starting...")

    try:
        from linuxav.app.controller import Controller
        from linuxav.ui.window import MainWindow

        controller = Controller()
        window = MainWindow(controller)

        status = controller.check_clamav_status()
        logger.info(f"ClamAV available: {status['available']}")
        logger.info(f"ClamAV version: {status['version']}")

        window.run()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
