from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, Any, Optional

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    preferences = Column(JSON, nullable=True)  # Store user interests/preferences
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    interactions = relationship("UserInteraction", back_populates="user")
    recommendations = relationship("UserRecommendation", back_populates="user")

class Business(Base):
    __tablename__ = "businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, nullable=True, index=True)
    category_name = Column(String(255), nullable=True, index=True)
    subcategory_name = Column(String(255), nullable=True, index=True)
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    address = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    status = Column(String(50), default="pending", index=True)
    features = Column(JSON, nullable=True)  # Store business features for content-based filtering
    is_featured = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    interactions = relationship("UserInteraction", back_populates="business")
    recommendations = relationship("UserRecommendation", back_populates="business")

class UserInteraction(Base):
    __tablename__ = "user_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    interaction_type = Column(String(50), nullable=False, index=True)  # 'view', 'click', 'like', 'share', 'contact'
    interaction_score = Column(Float, default=1.0)  # Weight for different interactions
    session_id = Column(String(255), nullable=True, index=True)
    interaction_metadata= Column(JSON, nullable=True)  # Additional interaction data
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="interactions")
    business = relationship("Business", back_populates="interactions")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_business', 'user_id', 'business_id'),
        Index('idx_user_interaction_type', 'user_id', 'interaction_type'),
        Index('idx_business_interaction_type', 'business_id', 'interaction_type'),
    )

class UserRecommendation(Base):
    __tablename__ = "user_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)
    recommendation_score = Column(Float, nullable=False)
    recommendation_type = Column(String(50), nullable=False, index=True)  # 'collaborative', 'content', 'hybrid'
    algorithm_version = Column(String(50), nullable=False)
    interaction_metadata= Column(JSON, nullable=True)  # Store reasoning/features
    is_served = Column(Boolean, default=False, index=True)
    is_clicked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="recommendations")
    business = relationship("Business", back_populates="recommendations")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_recommendations', 'user_id', 'recommendation_score'),
        Index('idx_user_type_score', 'user_id', 'recommendation_type', 'recommendation_score'),
    )

class BusinessCategory(Base):
    __tablename__ = "business_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("business_categories.id"), nullable=True)
    features = Column(JSON, nullable=True)  # Category-specific features
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Self-referential relationship for subcategories
    subcategories = relationship("BusinessCategory", backref="parent", remote_side=[id])

class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    preference_type = Column(String(50), nullable=False, index=True)  # 'category', 'feature', 'location'
    preference_value = Column(String(255), nullable=False)
    preference_weight = Column(Float, default=1.0)  # Importance score
    source = Column(String(50), default='explicit')  # 'explicit' or 'implicit'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_user_pref_type', 'user_id', 'preference_type'),
    )

class ModelTrainingJob(Base):
    __tablename__ = "model_training_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    model_type = Column(String(50), nullable=False, index=True)  # 'collaborative', 'content', 'hybrid'
    status = Column(String(50), default='pending', index=True)  # 'pending', 'running', 'completed', 'failed'
    training_params = Column(JSON, nullable=True)
    model_metrics = Column(JSON, nullable=True)  # Accuracy, precision, recall, etc.
    model_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    name = Column(String(255), nullable=True)
    browser_fingerprint = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    status = Column(String(50), default='active', index=True)  # 'active', 'closed', 'archived'
    metadata = Column(JSON, nullable=True)  # Additional session data
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at = Column(DateTime, nullable=True)
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_session_user', 'session_id', 'user_id'),
        Index('idx_session_email', 'session_id', 'email'),
        Index('idx_session_fingerprint', 'session_id', 'browser_fingerprint'),
    )

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), ForeignKey("chat_sessions.session_id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    sender = Column(String(50), nullable=False, index=True)  # 'user', 'bot'
    message_type = Column(String(50), default='text')  # 'text', 'image', 'file', etc.
    intent = Column(String(255), nullable=True)
    confidence = Column(Float, nullable=True)
    source = Column(String(50), nullable=True)  # 'knowledge_base', 'dialogflow', 'chatgpt', 'homepage_context'
    metadata = Column(JSON, nullable=True)  # Additional message data
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    
    __table_args__ = (
        Index('idx_session_sender', 'session_id', 'sender'),
        Index('idx_session_created', 'session_id', 'created_at'),
    )