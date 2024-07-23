import os
from datetime import date, datetime, timedelta

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, UniqueConstraint


POSTGRES_URL = os.environ['POSTGRES_URL']

engine = create_engine(POSTGRES_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class FrequencyData(Base):
    __tablename__ = "frequency_data"
    id = Column(Integer, primary_key=True, index=True)
    location = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    frequency = Column(Float)

    __table_args__ = (
        UniqueConstraint('location', 'timestamp', name='uq_location_timestamp'),
    )


Base.metadata.create_all(bind=engine)


def fetch_from_db(dataset: str, from_dt: date, to_dt: date) -> list[FrequencyData]:
    db = SessionLocal()
    return db.query(FrequencyData).filter(
        FrequencyData.location == dataset,
        FrequencyData.timestamp >= from_dt,
        FrequencyData.timestamp < to_dt + timedelta(days=1)
    ).all()


def save_to_db(dataset, data):
    db = SessionLocal()
    db_data = [FrequencyData(
        location=dataset,
        timestamp=datetime.fromisoformat(item[0]),
        frequency=item[1]
    ) for item in data]

    db.add_all(db_data)
    db.commit()
