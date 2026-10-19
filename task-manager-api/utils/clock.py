from datetime import datetime, timezone


def utc_now():
    # O schema legado armazena UTC sem offset. Normalizar na fronteira evita
    # misturar datetimes aware/naive e preserva a representação pública atual.
    return datetime.now(timezone.utc).replace(tzinfo=None)
