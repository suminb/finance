from finance.providers.dart import Dart
from finance.providers.kofia import Kofia
from finance.providers.miraeasset import Miraeasset
from finance.providers.provider import AssetValueProvider, Provider, \
    RecordProvider
from finance.providers.yahoo import Yahoo


__all__ = ['AssetValueProvider', 'Dart', 'Kofia', 'Miraeasset', 'Provider',
           'RecordProvider', 'Yahoo']


# NOTE: Abstract classes such as Provider, AssetValueProvider, and
# RecordProvider is defined under the `finance.providers.provider` module in
# order to avoid circular imports.

def is_valid_provider(provider):
    # NOTE: This is tightly coupled with Pandas DataFrame
    return provider in ['yahoo']