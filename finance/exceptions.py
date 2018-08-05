class NotFoundException(Exception):

    def __init__(self, target):
        self.target = target


class AccountNotFoundException(NotFoundException):

    def __repr__(self):
        return "Account '{0}' not found".format(self.target)


class AssetNotFoundException(NotFoundException):

    def __repr__(self):
        return "Asset '{0}' not found".format(self.target)


class AssetValueUnavailableException(Exception):
    pass


class InvalidTargetAssetException(Exception):
    pass
