from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey, Float, UniqueConstraint, Index
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class UserModel(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    phone = Column(String(50), default='', server_default='')
    created_at = Column(DateTime, default=utcnow, server_default='now()')
    is_admin = Column(Boolean, default=False, server_default='false')
    is_active = Column(Boolean, default=True, server_default='true')

    leads = relationship('LeadModel', back_populates='user', cascade='all, delete-orphan')
    search_history = relationship('SearchHistoryModel', back_populates='user', cascade='all, delete-orphan')
    message_logs = relationship('MessageLogModel', back_populates='user', cascade='all, delete-orphan')
    imap_settings = relationship('ImapSettingsModel', back_populates='user', uselist=False, cascade='all, delete-orphan')
    smtp_settings = relationship('SmtpSettingsModel', back_populates='user', uselist=False, cascade='all, delete-orphan')
    drip_configurations = relationship('DripConfigurationsModel', back_populates='user', uselist=False, cascade='all, delete-orphan')

class LeadModel(Base):
    __tablename__ = 'leads'
    id = Column(Integer, primary_key=True, autoincrement=True)
    place_id = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), default='', server_default='')
    address = Column(Text, default='', server_default='')
    website = Column(Text, default='', server_default='')
    rating = Column(Float, default=0.0, server_default='0.0')
    reviews = Column(Integer, default=0, server_default='0')
    category = Column(String(255), default='', server_default='')
    city = Column(String(255), default='', server_default='', index=True)
    priority = Column(String(50), default='LOW', server_default='LOW', index=True)
    whatsapp_number = Column(String(50), default='', server_default='')
    source = Column(String(100), default='google_maps', server_default='google_maps')
    contacted = Column(Boolean, default=False, server_default='false', index=True)
    contact_date = Column(DateTime, nullable=True)
    notes = Column(Text, default='', server_default='')
    instagram = Column(String(255), default='', server_default='')
    facebook = Column(String(255), default='', server_default='')
    custom_pitch = Column(Text, default='', server_default='')
    is_broken_website = Column(Boolean, default=False, server_default='false')
    line_type = Column(String(100), default='', server_default='')
    pipeline_stage = Column(String(100), default='NEW', server_default='NEW', index=True)
    email = Column(String(255), default='', server_default='')
    remind_date = Column(Date, nullable=True)
    remind_status = Column(String(100), default='', server_default='')
    audit_data = Column(Text, default='', server_default='')
    drip_sequence_active = Column(Boolean, default=True, server_default='true')
    last_followup_date = Column(DateTime, nullable=True)
    followup_count = Column(Integer, default=0, server_default='0')
    whatsapp_sent = Column(Boolean, default=False, server_default='false')
    social_task_status = Column(String(50), default='NONE', server_default='NONE')
    social_task_completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, server_default='now()', index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, server_default='now()')

    __table_args__ = (
        UniqueConstraint('place_id', 'user_id', name='leads_place_id_user_id_key'),
        Index('idx_leads_remind', 'remind_status', 'remind_date'),
        Index('idx_leads_drip', 'drip_sequence_active', 'pipeline_stage'),
    )

    user = relationship('UserModel', back_populates='leads')
    message_logs = relationship('MessageLogModel', back_populates='lead', cascade='all, delete-orphan')

class SearchHistoryModel(Base):
    __tablename__ = 'search_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    query = Column(Text, nullable=False)
    city = Column(String(255), nullable=False)
    results_count = Column(Integer, default=0, server_default='0')
    leads_count = Column(Integer, default=0, server_default='0')
    searched_at = Column(DateTime, default=utcnow, server_default='now()', index=True)
    deep_scan = Column(Boolean, default=False, server_default='false')
    zones = Column(Text, default='', server_default='')
    include_with_website = Column(Boolean, default=False, server_default='false')
    hide_saved = Column(Boolean, default=False, server_default='false')

    user = relationship('UserModel', back_populates='search_history')

class MessageLogModel(Base):
    __tablename__ = 'message_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey('leads.id', ondelete='CASCADE'), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    template_used = Column(String(255), default='', server_default='')
    message_sent = Column(Text, default='', server_default='')
    sent_at = Column(DateTime, default=utcnow, server_default='now()')
    opened = Column(Boolean, default=False, server_default='false')
    opened_at = Column(DateTime, nullable=True)
    open_count = Column(Integer, default=0, server_default='0')
    clicked = Column(Boolean, default=False, server_default='false')
    clicked_at = Column(DateTime, nullable=True)
    click_count = Column(Integer, default=0, server_default='0')
    clicked_links = Column(Text, default='', server_default='')
    is_reply = Column(Boolean, default=False, server_default='false', index=True)
    reply_body = Column(Text, default='', server_default='')

    user = relationship('UserModel', back_populates='message_logs')
    lead = relationship('LeadModel', back_populates='message_logs')

class PasswordResetsModel(Base):
    __tablename__ = 'password_resets'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    otp = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utcnow, server_default='now()')

class SystemSettingsModel(Base):
    __tablename__ = 'system_settings'
    key = Column(String(255), primary_key=True)
    value = Column(Text, nullable=False)

class ImapSettingsModel(Base):
    __tablename__ = 'imap_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=True)
    imap_host = Column(String(255), nullable=False)
    imap_port = Column(Integer, default=993, server_default='993')
    imap_email = Column(String(255), nullable=False)
    imap_password_encrypted = Column(Text, nullable=False)
    use_ssl = Column(Boolean, default=True, server_default='true')
    last_synced_at = Column(DateTime, nullable=True)

    user = relationship('UserModel', back_populates='imap_settings')

class SmtpSettingsModel(Base):
    __tablename__ = 'smtp_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=True)
    smtp_host = Column(String(255), nullable=False)
    smtp_port = Column(Integer, default=465, server_default='465')
    smtp_email = Column(String(255), nullable=False)
    smtp_password_encrypted = Column(Text, nullable=False)
    use_ssl = Column(Boolean, default=True, server_default='true')

    user = relationship('UserModel', back_populates='smtp_settings')

class DripConfigurationsModel(Base):
    __tablename__ = 'drip_configurations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=True)
    delay_days = Column(Integer, default=3, server_default='3')
    max_followups = Column(Integer, default=2, server_default='2')
    followup_subject = Column(String(255), default='Quick follow up regarding proposal', server_default='Quick follow up regarding proposal')
    followup_template = Column(Text, default='', server_default='')
    is_enabled = Column(Boolean, default=False, server_default='false')

    user = relationship('UserModel', back_populates='drip_configurations')
