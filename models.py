from sqlalchemy import Column, String, Float, Integer, DateTime
from database import Base # ask about app.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    # Genderize fields
    gender = Column(String, nullable=True)
    gender_probability = Column(Float, nullable=True)
    sample_size = Column(Integer, nullable=True)

    # Agify fields
    age = Column(Integer, nullable=True)
    age_group = Column(String, nullable=True)

    # Nationalize fields
    country_id = Column(String, nullable=True)
    country_probability = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False)
