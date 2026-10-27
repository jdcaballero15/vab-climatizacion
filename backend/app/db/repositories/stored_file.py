from app.db.models.stored_file import StoredFile
from app.db.repository import BaseRepository


class StoredFileRepository(BaseRepository[StoredFile]):
    model = StoredFile
