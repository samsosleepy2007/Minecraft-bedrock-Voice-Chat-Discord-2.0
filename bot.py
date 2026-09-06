from pathlib import Path
import base64
import lzma

# V1.7.3 hotfix layer over the lossless V1.7.0 source.
# Render can keep using: python bot.py
_payload_path = Path(__file__).with_name("bot_source.py.xz.b64")
_source = lzma.decompress(base64.b64decode(_payload_path.read_text(encoding="utf-8").strip())).decode("utf-8")


def _patch_once(old, new, label):
    """Apply one required source hotfix and fail loudly if the embedded source changed."""
    global _source
    if old not in _source:
        raise RuntimeError(f"V1.7.3 hotfix anchor not found: {label}")
    _source = _source.replace(old, new, 1)


_patch_once('BOT_VERSION = "1.7.0"', 'BOT_VERSION = "1.7.3"', "BOT_VERSION")
_patch_once('# --- ระบบจัดการห้องเสียง V1.7.0: Acoustic Groups only ---', '''async def ensure_bot_voice_connection(guild, target, reason="acoustic-test"):
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
                await asyncio.wait_for(vc.move_to(target), timeout=30.0)
            resolved = guild.voice_client
            resolved_channel = getattr(resolved, "channel", None) if resolved else None
            ok = bool(
                resolved
                and resolved.is_connected()
                and resolved_channel
                and resolved_channel.id == target.id
            )
            if not ok:
                actual_id = getattr(resolved_channel, "id", None)
                print(
                    f"[Voice {BOT_VERSION}] Voice reconciliation mismatch in guild {guild.id}: "
                    f"expected {target.id}, actual {actual_id} [{reason}]"
                )
            return ok
        print(f"[Voice {BOT_VERSION}] Connecting bot to {target.name} ({target.id}) [{reason}]")
        await target.connect(timeout=30.0, reconnect=True, self_deaf=False, self_mute=False)
        resolved = guild.voice_client
        resolved_channel = getattr(resolved, "channel", None) if resolved else None
        ok = bool(
            resolved
            and resolved.is_connected()
            and resolved_channel
            and resolved_channel.id == target.id
        )
        if not ok:
            actual_id = getattr(resolved_channel, "id", None)
            print(
                f"[Voice {BOT_VERSION}] Voice connect verification mismatch in guild {guild.id}: "
                f"expected {target.id}, actual {actual_id} [{reason}]"
            )
        return ok
    except asyncio.TimeoutError:
        print(
            f"[Voice {BOT_VERSION}] Bot voice reconciliation timed out in guild {guild.id}, "
            f"channel {target.id} [{reason}]"
        )
        return False
    except Exception as exc:
        print(f"[Voice {BOT_VERSION}] Bot voice connection failed in guild {guild.id}, channel {target.id}: {type(exc).__name__}: {exc}")
        return False


# --- ระบบจัดการห้องเสียง V1.7.3: Acoustic Groups only ---''', "voice helper")
_patch_once('''            if mem == guild.me:
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
''', "acoustic bot routing")
_patch_once('''        await assign_acoustic_groups_in_category(
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

        # Test fallback remains connection-only. Do not force botvc to follow the
        # Test owner while they are outside Minecraft acoustic range.
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
''', "test fallback")
exec(compile(_source, "bot_v1.7.3.py", "exec"), globals(), globals())
