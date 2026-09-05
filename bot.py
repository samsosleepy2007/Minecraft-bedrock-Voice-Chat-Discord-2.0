from pathlib import Path
import base64
import lzma

# V1.7.0 source is stored losslessly as an XZ+Base64 payload because the
# connected GitHub writer cannot upload the full source file in one request.
# Render can keep using: python bot.py
_payload_path = Path(__file__).with_name("bot_source.py.xz.b64")
_payload = _payload_path.read_text(encoding="utf-8").strip()
_source = lzma.decompress(base64.b64decode(_payload)).decode("utf-8")
exec(compile(_source, "bot_v1.7.0.py", "exec"), globals(), globals())
