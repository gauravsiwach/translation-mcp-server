from sqlalchemy import Column, BigInteger, String, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class PepsiLanguage(Base):
    __tablename__ = "pepsi_languages"
    __table_args__ = {"schema": "customer_uat_ind", "extend_existing": True}
    language_code = Column(String(10), primary_key=True)
    language = Column(String(100), nullable=False)
    created_datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PepsiTranslation(Base):
    __tablename__ = "pepsi_translations"
    __table_args__ = {"schema": "customer_uat_ind", "extend_existing": True}
    id = Column(BigInteger, primary_key=True)
    label = Column(Text, nullable=False)
    language_code = Column(String(10), ForeignKey("customer_uat_ind.pepsi_languages.language_code"), nullable=False)
    translation = Column(Text, nullable=False)
    type = Column(String(255), nullable=True)
    created_datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
