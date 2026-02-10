from sqlalchemy import create_engine, Column, Integer, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./formulations.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Formulation(Base):
    __tablename__ = "formulations"
    
    id = Column(Integer, primary_key=True, index=True)
    request = Column(Text, nullable=False)
    formulation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Save (Ctrl+S) and close.

---

### Restore requirements.txt

**Type:**
```
notepad requirements.txt
```

Press Enter.

**Delete everything and paste:**
```
fastapi==0.104.1
uvicorn==0.24.0
anthropic==0.79.0
python-dotenv==1.0.0
sqlalchemy==2.0.25
```

Save (Ctrl+S) and close.

---

### Delete auth.py

**Type:**
```
del auth.py