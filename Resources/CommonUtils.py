import logging


class Utils:
    """
    Small library for static methods that may come in handy
    """
    @staticmethod
    def human_readable_filesize(num, suffix='B'):  # Copied from https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
        """
        Takes a number (in bytes) and converts it to a human readable form.
        :param num: number in bytes
        :type num:
        :param suffix: Suffix for use of something other than bytes
        :type suffix:
        :return: Returns human readable string
        :rtype: String
        """
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                return "{:3.2f} {}{}".format(num, unit, suffix)
            num /= 1024.0
        # changed to newer formatting style.
        return "{:.1f} {}{}".format(num, 'Yi', suffix)

    @staticmethod
    def create_logger(log_to_console=True):
        """
        Creates a logger object to log output to file and optionally console
        :param log_to_console: Whether to log output to the console
        :return: logger object
        """
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        log_formatter = logging.Formatter("%(asctime)s: [%(name)s]: [%(levelname)s]: %(message)s", datefmt='%m/%d/%Y %I:%M:%S %p')

        # file_handler = logging.FileHandler('SR.log')
        file_handler = logging.handlers.RotatingFileHandler('SR.log', backupCount=5, maxBytes=5242880)  # creates new log at 5 MB
        file_handler.setFormatter(log_formatter)
        logger.addHandler(file_handler)

        if log_to_console is True:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(log_formatter)
            logger.addHandler(console_handler)
        return logger
