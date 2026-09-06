from pathlib import Path
import base64
import lzma

# V1.7.4 hotfix layer over the lossless V1.7.0 source.
# Render can keep using: python bot.py
_payload_path = Path(__file__).with_name("bot_source.py.xz.b64")
_source = lzma.decompress(base64.b64decode(_payload_path.read_text(encoding="utf-8").strip())).decode("utf-8")


def _patch_once(old, new, label):
    """Apply one required source hotfix and fail loudly if the embedded source changed."""
    global _source
    if old not in _source:
        raise RuntimeError(f"V1.7.4 hotfix anchor not found: {label}")
    _source = _source.replace(old, new, 1)


_patch_once('BOT_VERSION = "1.7.0"', 'BOT_VERSION = "1.7.4"', "BOT_VERSION")

# V1.7.4 owns player move throttling with a per-member wrapper below. Disable
# the legacy global 3-second gate so different Minecraft guilds can use their
# own move_delay and so one member never serializes another member's moves.
_patch_once('MOVE_COOLDOWN = 3.0', 'MOVE_COOLDOWN = 0.0', "legacy MOVE_COOLDOWN")

_patch_once('# --- ระบบจัดการห้องเสียง V1.7.0: Acoustic Groups only ---', '''# --- V1.7.4 runtime Voice Move Delay -----------------------------------------
# Addon Protocol V3 may include optional move_delay (0.0-5.0 seconds).
# Capture it as soon as aiohttp decodes /update_coords JSON, then enforce the
# delay per Discord member at the actual Member.move_to boundary. This keeps
# the setting local to each guild and prevents a global sleep/queue.
VC_DEFAULT_MOVE_DELAY = 3.0
vc_move_delay_by_guild = {}
vc_member_last_move = {}

_vc_original_request_json = web.Request.json
async def _vc_request_json_with_move_delay(request, *args, **kwargs):
    payload = await _vc_original_request_json(request, *args, **kwargs)
    if isinstance(payload, dict) and payload.get("protocol_version") == 3:
        raw_guild_id = payload.get("guild_id")
        try:
            guild_id = int(str(raw_guild_id).strip())
        except (TypeError, ValueError):
            guild_id = None
        if guild_id is not None:
            try:
                delay = float(payload.get("move_delay", VC_DEFAULT_MOVE_DELAY))
                if not math.isfinite(delay):
                    raise ValueError("non-finite move_delay")
            except (TypeError, ValueError):
                delay = VC_DEFAULT_MOVE_DELAY
            delay = max(0.0, min(5.0, round(delay, 1)))
            previous = vc_move_delay_by_guild.get(guild_id)
            vc_move_delay_by_guild[guild_id] = delay
            if previous is None or abs(previous - delay) > 1e-9:
                print(f"[Voice {BOT_VERSION}] Guild {guild_id} move delay = {delay:.1f}s")
    return payload
web.Request.json = _vc_request_json_with_move_delay

_vc_original_member_move_to = discord.Member.move_to
async def _vc_rate_limited_member_move_to(member, channel, *, reason=None):
    guild = getattr(member, "guild", None)
    guild_id = getattr(guild, "id", None)
    member_id = getattr(member, "id", None)
    current_voice = getattr(member, "voice", None)
    current_channel = getattr(current_voice, "channel", None) if current_voice else None
    target_id = getattr(channel, "id", None) if channel is not None else None

    # Never spend a Discord move request when the desired state already matches.
    if current_channel is not None and target_id is not None and current_channel.id == target_id:
        return None

    delay = vc_move_delay_by_guild.get(guild_id, VC_DEFAULT_MOVE_DELAY)
    key = (guild_id, member_id)
    now = time.monotonic()
    last = vc_member_last_move.get(key, -1e12)
    if delay > 0.0 and (now - last) < delay:
        return None

    result = await _vc_original_member_move_to(member, channel, reason=reason)
    vc_member_last_move[key] = time.monotonic()
    return result

discord.Member.move_to = _vc_rate_limited_member_move_to


async def ensure_bot_voice_connection(guild, target, reason="acoustic-test"):
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


# --- ระบบจัดการห้องเสียง V1.7.4: Acoustic Groups only ---''', "voice helper + move delay")
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
exec(compile(_source, "bot_v1.7.4.py", "exec"), globals(), globals())
