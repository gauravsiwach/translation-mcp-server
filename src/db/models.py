from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    JSON,
    DateTime,
    func,
    Text,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Market(Base):
    __tablename__ = "markets"
    id = Column(Integer, primary_key=True)
    code = Column(String(8), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    site_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)

class MarketLocale(Base):
    __tablename__ = "market_locales"
    id = Column(Integer, primary_key=True)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False)
    locale_code = Column(String(32), nullable=False)
    is_default = Column(Boolean, default=False)

class Translation(Base):
    __tablename__ = "translations"
    id = Column(Integer, primary_key=True)
    key = Column(String(255), nullable=False)
    market_id = Column(Integer, ForeignKey("markets.id"), nullable=False)
    locale_code = Column(String(32), nullable=False)
    value = Column(Text, nullable=True)
    default_text = Column(Text, nullable=True)
    context = Column(Text, nullable=True)
    screen_id = Column(String(128), nullable=True)
    figma_node_id = Column(String(128), nullable=True)
    batch_id = Column(String(64), nullable=True, index=True)
    status = Column(String(32), default="CREATED")
    environment = Column(String(32), default="QA")
    confidence = Column(Float, nullable=True)
    version = Column(Integer, default=1)
    created_by = Column(String(128), nullable=True)
    updated_by = Column(String(128), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("key", "market_id", "locale_code", "environment", name="uq_translation_unique"),
    )

class TranslationVersion(Base):
    __tablename__ = "translation_versions"
    id = Column(Integer, primary_key=True)
    translation_id = Column(Integer, ForeignKey("translations.id"), nullable=False)
    version = Column(Integer, nullable=False)
    value = Column(Text, nullable=True)
    status = Column(String(32), nullable=True)
    changed_by = Column(String(128), nullable=True)
    change_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    action = Column(String(64), nullable=False)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(Integer, nullable=True)
    market_code = Column(String(8), nullable=True)
    details = Column(JSON, nullable=True)
    performed_by = Column(String(128), nullable=True)
    performed_at = Column(DateTime, server_default=func.now())

class FeedbackCorrection(Base):
    __tablename__ = "feedback_corrections"
    id = Column(Integer, primary_key=True)
    translation_id = Column(Integer, ForeignKey("translations.id"), nullable=True)
    key = Column(String(255), nullable=False)
    market_code = Column(String(8), nullable=False)
    locale_code = Column(String(32), nullable=False)
    ai_original_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)
    corrected_by = Column(String(128), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class Promotion(Base):
    __tablename__ = "promotions"
    id = Column(Integer, primary_key=True)
    market_code = Column(String(8), nullable=False)
    env_from = Column(String(32), nullable=False)
    env_to = Column(String(32), nullable=False)
    keys_promoted = Column(JSON, nullable=True)
    status = Column(String(32), nullable=True)
    promoted_by = Column(String(128), nullable=True)
    snapshot = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
