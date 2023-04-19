from sqlalchemy import Integer, Float, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

from lib.util import ConsumptionEntry

class Base(DeclarativeBase):
    pass

class DBConsumptionEntry(Base):
    __tablename__ = "fuel_consumption_tracking"

    id:       Mapped[int]   = mapped_column(primary_key=True, autoincrement=True)
    odometer: Mapped[int]   = mapped_column(Integer)
    distance: Mapped[float] = mapped_column(Float)
    liters:   Mapped[float] = mapped_column(Float)
    entry_ts: Mapped[float] = mapped_column(Float)

    consumption:       Mapped[float] = mapped_column(Float)
    price_per_liter:   Mapped[float] = mapped_column(Float)
    consumption_price: Mapped[float] = mapped_column(Float)

class DataManager():
    def __init__(self, sqlite_path):
        self.db_engine = create_engine(f"sqlite:///{sqlite_path}", echo=True)
        Base.metadata.create_all(self.db_engine)

    def add_entry(self, entry: ConsumptionEntry):
        with Session(self.db_engine) as session:
            entry = DBConsumptionEntry(
                odometer = entry.odometer,
                distance = entry.distance,
                liters   = entry.liters,
                entry_ts = entry.entry_ts,
                consumption = entry.consumption,
                price_per_liter = entry.price_per_liter,
                consumption_price = entry.consumption_price
            )

            session.add(entry)
            session.commit()

    def delete_entry(self, id):
        with Session(self.db_engine) as session:
            entry = session.get(DBConsumptionEntry, id)
            session.delete(entry)
            session.commit()

    def list_entries(self, count):
        with Session(self.db_engine) as session:
            result = session.execute(
                select(DBConsumptionEntry).order_by(DBConsumptionEntry.id.desc()).limit(count),
                execution_options={"prebuffer_rows": True}
            )
        return result.scalars()

    def historical_consumption(self, timeframe):
        with Session(self.db_engine) as session:
            pass

    def historical_price_per_liter(self, timeframe):
        with Session(self.db_engine) as session:
            pass