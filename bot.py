from pathlib import Path
import base64
import lzma

# V1.6.4 source is stored losslessly as an XZ+Base64 payload because the
# connected GitHub writer cannot upload the 77 KB source file in one request.
# This loader reconstructs the exact original bot.py source in memory and runs it.
_payload_path = Path(__file__).with_name("bot_source.py.xz.b64")
_payload = _payload_path.read_text(encoding="utf-8").strip()
_source = lzma.decompress(base64.b64decode(_payload)).decode("utf-8")
exec(compile(_source, "bot_v1.6.4.py", "exec"), globals(), globals())
