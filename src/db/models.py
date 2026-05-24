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
    
    # New columns for status workflow, Figma integration, and audit tracking
    status = Column(String(32), default='PENDING_REVIEW')
    figma_node_id = Column(String(128), nullable=True)
    figma_file_key = Column(String(255), nullable=True)
    figma_screenshot_url = Column(Text, nullable=True)
    created_by = Column(String(128), nullable=True)
    updated_by = Column(String(128), nullable=True)


class PepsiFeedbackCorrection(Base):
    __tablename__ = "pepsi_feedback_corrections"
    __table_args__ = {"schema": "customer_uat_ind", "extend_existing": True}
    
    id = Column(BigInteger, primary_key=True)
    translation_id = Column(BigInteger, ForeignKey("customer_uat_ind.pepsi_translations.id"), nullable=True)
    label = Column(Text, nullable=False)
    language_code = Column(String(10), nullable=False)
    ai_original_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)
    correction_reason = Column(Text, nullable=True)
    corrected_by = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
