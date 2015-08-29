
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
