from django.utils import timezone
from django.db import models
from django.conf import settings
from django.db.models import F
from decimal import Decimal

class Portfolio(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    remarks = models.TextField(blank=True, null=True)
    dateCreated = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name
    
    def total_value(self):
        total = 0
        for asset in self.asset_set.all():
            total += asset.units * asset.averagePrice
        return total
    
    def total_fees(self):
        total = 0
        for transaction in self.transaction_set.all():
            total += transaction.fee
        return total
    
    def total_RealisedPL(self):
        total = 0
        for transaction in self.transaction_set.all():
            total += transaction.realisedPL()
        return total

class Asset(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    ticker = models.CharField(max_length=10)
    type = models.CharField(max_length=50, default='Others')
    sector = models.CharField(max_length=50, default='Others')
    units = models.DecimalField(max_digits=20, decimal_places=3, default=0)
    averagePrice = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.ticker
    
    def value(self):
        return self.units * self.averagePrice
    
    
class Transaction(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=[('buy', 'Buy'), ('sell', 'Sell')])
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True)
    asset_name = models.CharField(max_length=200)
    ticker = models.CharField(max_length=10)
    units = models.DecimalField(max_digits=20, decimal_places=5)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transaction_date = models.DateTimeField(default=timezone.now)

    def realisedPL(self):
        if self.transaction_type == 'buy':
            return 0
        else:
            return (self.price - self.asset.averagePrice) * self.units
        

    def save(self, *args, **kwargs):
        # Call the "real" save() method.
        super().save(*args, **kwargs)

        # Check if the asset exists in the portfolio.
        if self.asset is not None:
            asset, created = Asset.objects.get_or_create(
                portfolio=self.portfolio,
                name=self.asset.name,
                defaults={
                    'ticker': self.asset.ticker,
                    'type': self.asset.type,
                    'sector': self.asset.sector,
                    'units': 0 if self.transaction_type == 'sell' else self.units,
                    'averagePrice': self.price
                }
            )

        if not created:
            if self.transaction_type == 'buy':
                asset.units = F('units') + self.units
                asset.averagePrice = (F('averagePrice') * F('units') + self.units * self.price) / (F('units') + self.units)
            else:  # sell
                asset.units = F('units') - self.units
                asset.save()
                asset.refresh_from_db()
                if asset.units == Decimal('0.000'):
                    asset.delete()
                    return
            asset.save()

                        
    def delete(self, *args, **kwargs):
        # Check if the asset exists in the transaction.
        if self.asset is not None:
            asset = Asset.objects.get(name=self.asset.name, portfolio=self.portfolio)
            if asset:
                if self.transaction_type == 'buy':
                    asset.units = F('units') - self.units
                    asset.save()
                    asset.refresh_from_db()
                    if asset.units > 0:
                        asset.averagePrice = (asset.averagePrice * asset.units - self.units * self.price) / asset.units
                    else:
                        asset.averagePrice = 0
                else:  # sell
                    asset.units = F('units') + self.units
                    asset.save()
                    asset.refresh_from_db()
                    if asset.units > 0:
                        asset.averagePrice = (asset.averagePrice * asset.units + self.units * self.price) / asset.units
                    else:
                        asset.averagePrice = 0
                asset.save()
                if asset.units == Decimal('0.000'):
                    asset.delete()
                    

        # Call the "real" delete() method.
        super().delete(*args, **kwargs)
            
