from sqlalchemy import ForeignKey, Integer, Float, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from lib.util import ConsumptionEntry, Car

class Base(DeclarativeBase):
    pass

class DBCar(Base):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)

class DBPeople(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    t_id: Mapped[int] = mapped_column(Integer)

class DBConsumptionEntry(Base):
    __tablename__ = "fuel_consumption_tracking"

    id:       Mapped[int]     = mapped_column(primary_key=True, autoincrement=True)
    car_id:   Mapped[DBCar]   = mapped_column(ForeignKey("cars.id"))
    odometer: Mapped[int]     = mapped_column(Integer)
    distance: Mapped[float]   = mapped_column(Float)
    liters:   Mapped[float]   = mapped_column(Float)
    entry_ts: Mapped[float]   = mapped_column(Float)

    consumption:       Mapped[float] = mapped_column(Float)
    price_per_liter:   Mapped[float] = mapped_column(Float)
    consumption_price: Mapped[float] = mapped_column(Float)

class DataManager():
    def __init__(self, sqlite_path):
        self.db_engine = create_engine(f"sqlite:///{sqlite_path}")
        Base.metadata.create_all(self.db_engine)

    def add_new_car(self, car: Car):
        with Session(self.db_engine) as session:
            car = DBCar(
                name = car.name
            )
            session.add(car)
            session.commit()

    def list_cars(self):
        with Session(self.db_engine) as session:
            result = session.execute(
                select(DBCar).order_by(DBCar.id.desc()),
                execution_options={"prebuffer_rows": True}
            )
        return result.scalars()

    def get_car(self, id):
        with Session(self.db_engine) as session:
            result = session.execute(
                select(DBCar).where(DBCar.id == id),
                execution_options={"prebuffer_rows": True}
            )
        return result.scalars()

    def add_fc_entry(self, entry: ConsumptionEntry):
        with Session(self.db_engine) as session:
            entry = DBConsumptionEntry(
                odometer = entry.odometer,
                distance = entry.distance,
                liters   = entry.liters,
                entry_ts = entry.entry_ts,
                consumption = entry.consumption,
                price_per_liter = entry.price_per_liter,
                consumption_price = entry.consumption_price,
                car_id = entry.car_id
            )

            session.add(entry)
            session.commit()

    def delete_fc_entry(self, id):
        with Session(self.db_engine) as session:
            entry = session.get(DBConsumptionEntry, id)
            session.delete(entry)
            session.commit()

    def list_fc_entries(self, count):
        with Session(self.db_engine) as session:
            result = session.execute(
                select(DBConsumptionEntry).order_by(DBConsumptionEntry.id.desc()).limit(count),
                execution_options={"prebuffer_rows": True}
            )
        return result.scalars()

    def get_historical_data(self, timeframe, car_id):
        with Session(self.db_engine) as session:
            result = session.execute(
                select(DBConsumptionEntry).order_by(DBConsumptionEntry.id.desc()).where(DBConsumptionEntry.car_id == car_id),
                #.where(DBConsumptionEntry.entry_ts > timeframe)
                execution_options={"prebuffer_rows": True}
            )
        return result.scalars()
