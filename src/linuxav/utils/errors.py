class LinuxAVError(Exception):
    pass


class ScanError(LinuxAVError):
    pass


class UpdateError(LinuxAVError):
    pass


class ConfigurationError(LinuxAVError):
    pass


class ValidationError(LinuxAVError):
    pass
