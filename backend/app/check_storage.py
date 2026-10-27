"""Comprueba el bucket configurado con el mismo camino que usan las apps.

Firma una subida, sube un archivo de prueba, lo lee con una URL firmada y lo borra.
Se corre después de configurar el bucket (docs/workflow/despliegue.md).

Uso:
    python -m app.check_storage
"""

import asyncio
import sys
import urllib.request
import uuid

from app.core.storage import get_storage

_BODY = b"prueba de bucket"
_TYPE = "text/plain"


def main() -> None:
    storage = get_storage()
    key = f"checks/{uuid.uuid4()}"
    try:
        put = urllib.request.Request(  # noqa: S310 (URL firmada del bucket configurado)
            storage.upload_url(key, _TYPE, len(_BODY)),
            data=_BODY,
            method="PUT",
            headers={"Content-Type": _TYPE},
        )
        urllib.request.urlopen(put, timeout=10).close()  # noqa: S310
        stored = asyncio.run(storage.head(key))
        if stored is None or stored.size_bytes != len(_BODY):
            sys.exit("El bucket no tiene el archivo de prueba después de subirlo.")
        with urllib.request.urlopen(storage.download_url(key), timeout=10) as response:  # noqa: S310
            if response.read() != _BODY:
                sys.exit("El archivo leído no coincide con el subido.")
    finally:
        storage.delete(key)
    print("Bucket OK")


if __name__ == "__main__":
    main()
