from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, JSON

Base = declarative_base()


class People(Base):
    __tablename__ = 'sw'

    id = Column(Integer, primary_key=True)
    json = Column(JSON)
