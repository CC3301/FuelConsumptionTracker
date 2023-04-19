from datetime import datetime

class ConsumptionEntry():
    def __init__(self, odometer, distance, liters, total_period_price):
        self.odometer = odometer
        self.distance = distance
        self.liters = liters
        self.total_period_price = total_period_price
        self.entry_ts = datetime.now().timestamp()

        self.consumption = self.liters / self.distance * 100
        self.price_per_liter = self.total_period_price / self.liters
        self.consumption_price = self.consumption * self.price_per_liter