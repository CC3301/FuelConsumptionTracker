import os
from quickchart import QuickChart
from datetime import datetime

class GraphingHelper():
    def __init__(self, dm, tmpdir):
        self.dm = dm
        self._tmpdir = tmpdir

        if not os.path.isdir(self._tmpdir):
            os.mkdir(self._tmpdir)

    def create_historical_consumption_graph(self, timeframe, car_id):
        data = self.dm.get_historical_data(timeframe, car_id)
        chart = QuickChart()
        chart.width = 500
        chart.height = 300
        chart.device_pixel_ratio = 2.0

        chart_labels = []
        chart_datapoints = []

        for d in data:
            chart_labels.append(datetime.strftime(datetime.fromtimestamp(d.entry_ts), '%d.%m.%Y %H:%M'))
            chart_datapoints.append(d.consumption)

        chart.config = {
            "type": "line",
            "data": {
                "labels": chart_labels[::-1],
                "datasets": [{
                    "label": "l/100km",
                    "data": chart_datapoints[::-1]
                }]
            }
        }

        print(chart.get_short_url())
        return chart.get_bytes()

    
    def create_historical_price_per_liter_graph(self, timeframe, car_id):
        data = self.dm.get_historical_data(timeframe, car_id)