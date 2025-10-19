uvicorn app.main:app --reload

## STRUCTURE
/api: API router, endpoints
/core: config, security
/data: data files
/db: database, crud operations, e.g. class CRUDUser: def get_by_email() def create() etc.
/models: SQLAlchemy database models, e.g. definition of class User(Base)
/schemas: Pydantic models for request/response validation
/services: business logic separate from API routes and DB operations
/utils: helpers 
dependencies: shared dependencies like database sessions, get_current_user()

