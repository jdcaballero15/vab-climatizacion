"""Crea el bucket configurado si no existe. Solo para MinIO local.

En la nube (Cloudflare R2) el bucket se crea desde el panel: ver docs/workflow/despliegue.md.

Uso:
    python -m app.create_bucket
"""

from app.core.config import get_settings
from app.core.storage import get_storage


def main() -> None:
    bucket = get_settings().s3_bucket
    created = get_storage().ensure_bucket()
    print(f"Bucket '{bucket}' creado." if created else f"El bucket '{bucket}' ya existe.")


if __name__ == "__main__":
    main()
