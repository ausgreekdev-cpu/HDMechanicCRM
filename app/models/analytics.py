from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Numeric, Text, DateTime, Boolean, JSON
from app.database import Base


class AppSession(Base):
    """Track mobile/web app sessions"""
    __tablename__ = "app_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    platform = Column(String(20))  # android, ios, web
    app_version = Column(String(20))
    device_info = Column(String(200))
    started_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    page_views = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class PageView(Base):
    """Track page/route views"""
    __tablename__ = "page_views"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer)
    user_id = Column(Integer)
    path = Column(String(300))
    load_time_ms = Column(Integer)
    platform = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)


class FeatureUsage(Base):
    """Track which features are used"""
    __tablename__ = "feature_usage"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    feature = Column(String(100))  # work_order, invoice, scrap_pickup, etc
    action = Column(String(50))    # create, view, edit, delete
    count = Column(Integer, default=1)
    last_used_at = Column(DateTime, default=datetime.utcnow)


class CrashReport(Base):
    """Track mobile app crashes"""
    __tablename__ = "crash_reports"
    id = Column(Integer, primary_key=True)
    platform = Column(String(20))
    app_version = Column(String(20))
    error_type = Column(String(100))
    error_message = Column(Text)
    stack_trace = Column(Text)
    device_info = Column(String(200))
    reported_at = Column(DateTime, default=datetime.utcnow)
    is_resolved = Column(Boolean, default=False)


class DailyMetrics(Base):
    """Aggregated daily metrics"""
    __tablename__ = "daily_metrics"
    id = Column(Integer, primary_key=True)
    metric_date = Column(String(10))  # YYYY-MM-DD
    active_users = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)
    total_page_views = Column(Integer, default=0)
    new_work_orders = Column(Integer, default=0)
    new_customers = Column(Integer, default=0)
    revenue = Column(Numeric(10,2), default=0)
    scrap_weight_kg = Column(Float, default=0)
    avg_session_minutes = Column(Float, default=0)
