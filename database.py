from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Указываем, что база будет храниться в локальном файле ege.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./ege.db"

# Создаем "движок" для подключения
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Настраиваем сессию (канал связи с базой)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем базовый класс, от которого будут наследоваться все наши таблицы
Base = declarative_base()