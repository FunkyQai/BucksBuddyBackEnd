from rest_framework import serializers
from .models import Transaction
from .models import Asset

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'portfolio', 'transaction_type', 'asset', 'asset_name', 'ticker', 'units', 'price', 'fee', 'transaction_date']


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['id', 'portfolio', 'name', 'ticker', 'type', 'sector', 'units', 'averagePrice']