from pathlib import Path
import base64
import lzma

# V1.7.2 hotfix layer over the lossless V1.7.0 source.
# Render can keep using: python bot.py
_payload_path = Path(__file__).with_name("bot_source.py.xz.b64")
_source = lzma.decompress(base64.b64decode(_payload_path.read_text(encoding="utf-8").strip())).decode("utf-8")
_source = _source.replace('BOT_VERSION = "1.7.0"', 'BOT_VERSION = "1.7.2"', 1)
_source = _source.replace('# --- ระบบจัดการห้องเสียง V1.7.0: Acoustic Groups only ---', '''async def ensure_bot_voice_connection(guild, target, reason="acoustic-test"):
    """Reliable Discord bot VoiceClient connect/move for Test and Acoustic Groups."""
    if not isinstance(target, discord.VoiceChannel):
        print(f"[Voice {BOT_VERSION}] Invalid voice target: {target!r}")
        return False
    me = guild.me
    if me is None:
        print(f"[Voice {BOT_VERSION}] guild.me unavailable in guild {guild.id}")
        return False
    perms = target.permissions_for(me)
    if not perms.view_channel or not perms.connect:
        print(f"[Voice {BOT_VERSION}] Missing View Channel/Connect for {target.name} ({target.id})")
        return False
    vc = guild.voice_client
    try:
        if vc is not None and not vc.is_connected():
            try:
                await vc.disconnect(force=True)
            except Exception as exc:
                print(f"[Voice {BOT_VERSION}] Failed to clear stale VoiceClient: {exc!r}")
            vc = None
        if vc is not None:
            current_channel = getattr(vc, "channel", None)
            if current_channel is None or current_channel.id != target.id:
                print(f"[Voice {BOT_VERSION}] Moving bot to {target.name} ({target.id}) [{reason}]")
                await vc.move_to(target)
            return True
        print(f"[Voice {BOT_VERSION}] Connecting bot to {target.name} ({target.id}) [{reason}]")
        await target.connect(timeout=30.0, reconnect=True, self_deaf=False, self_mute=False)
        return bool(guild.voice_client and guild.voice_client.is_connected())
    except Exception as exc:
        print(f"[Voice {BOT_VERSION}] Bot voice connection failed in guild {guild.id}, channel {target.id}: {type(exc).__name__}: {exc}")
        return False


# --- ระบบจัดการห้องเสียง V1.7.2: Acoustic Groups only ---''', 1)
_source = _source.replace('''            if mem == guild.me:
                try:
                    if guild.voice_client:
                        if guild.voice_client.channel.id != target.id:
                            await guild.voice_client.move_to(target)
                    else:
                        await target.connect()
                except Exception:
                    pass
                continue
''', '''            if mem == guild.me:
                await ensure_bot_voice_connection(guild, target, reason="acoustic-group")
                continue
''', 1)
_source = _source.replace('''        await assign_acoustic_groups_in_category(
            guild,
            snapshot_acoustic_groups,
            tag_to_member,
            cat,
            start_channel,
            taken_rooms,
            curr,
            excluded_user_ids=in_call_users
        )
''', '''        await assign_acoustic_groups_in_category(
            guild,
            snapshot_acoustic_groups,
            tag_to_member,
            cat,
            start_channel,
            taken_rooms,
            curr,
            excluded_user_ids=in_call_users
        )

        # Test fallback: always give botvc a deterministic Discord voice target
        # even when the acoustic group is only [botvc] or the room pool is empty.
        if session_matches_runtime and botvc_present and not (guild.voice_client and guild.voice_client.is_connected()):
            test_target = None
            owner_id = (session or {}).get("owner_user_id")
            owner_member = guild.get_member(owner_id) if owner_id else None
            if owner_member and owner_member.voice and owner_member.voice.channel and owner_member.voice.channel.category_id == cat.id:
                test_target = owner_member.voice.channel
            if test_target is None:
                test_target = next((c for c in cat.channels if isinstance(c, discord.VoiceChannel) and c.id != start_channel.id), None)
            if test_target is None:
                test_target = start_channel
            await ensure_bot_voice_connection(guild, test_target, reason="test-fallback")
''', 1)
exec(compile(_source, "bot_v1.7.2.py", "exec"), globals(), globals())
