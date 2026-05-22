from app.database import Base, engine
import app.models  # noqa

if __name__ == '__main__':
    Base.metadata.create_all(bind=engine)
    print('DB initialized')
