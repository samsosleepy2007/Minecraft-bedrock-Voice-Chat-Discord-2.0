from pathlib import Path
import base64
import lzma

# V1.7.5 hotfix layer over the lossless V1.7.0 source.
# Render can keep using: python bot.py
_payload_path = Path(__file__).with_name("bot_source.py.xz.b64")
_source = lzma.decompress(base64.b64decode(_payload_path.read_text(encoding="utf-8").strip())).decode("utf-8")


def _patch_once(old, new, label):
    """Apply one required source hotfix and fail loudly if the embedded source changed."""
    global _source
    if old not in _source:
        raise RuntimeError(f"V1.7.5 hotfix anchor not found: {label}")
    _source = _source.replace(old, new, 1)


_patch_once('BOT_VERSION = "1.7.0"', 'BOT_VERSION = "1.7.5"', "BOT_VERSION")

# V1.7.5 owns voice stability delay at the desired-state boundary below. The
# old V1.7.0 cooldown is disabled so it cannot silently add a second ~3s gate.
_patch_once('MOVE_COOLDOWN = 3.0', 'MOVE_COOLDOWN = 0.0', "legacy MOVE_COOLDOWN")

_patch_once('# --- ระบบจัดการห้องเสียง V1.7.0: Acoustic Groups only ---', '''# --- V1.7.5 desired-state Voice Move Delay ----------------------------------
# Protocol V3 optional move_delay means: after the desired Discord destination
# changes, that destination must remain stable for N seconds before the move.
# This is a debounce/stability timer, NOT time-since-last-move cooldown.
import contextvars

VC_DEFAULT_MOVE_DELAY = 3.0
vc_move_delay_by_guild = {}
vc_member_pending = {}
vc_member_generation = {}
vc_member_recent_target = {}
vc_move_events_by_guild = {}
_vc_request_guild_context = contextvars.ContextVar("vc_request_guild_id", default=None)


def _vc_channel_id(channel):
    return getattr(channel, "id", None) if channel is not None else None


def _vc_current_channel_id(member):
    voice = getattr(member, "voice", None)
    channel = getattr(voice, "channel", None) if voice else None
    return getattr(channel, "id", None) if channel is not None else None


def _vc_cancel_pending(key, *, reason="superseded"):
    state = vc_member_pending.pop(key, None)
    if not state:
        return
    task = state.get("task")
    if task is not None and not task.done():
        task.cancel()
    if reason:
        print(
            f"[Voice {BOT_VERSION}] Delay cancel {state.get('member_name')} -> "
            f"{state.get('target_name')} [{reason}]"
        )


def _vc_event(guild_id, **values):
    if guild_id is None:
        return
    event = vc_move_events_by_guild.setdefault(guild_id, {})
    event.update(values)


async def _vc_execute_pending_move(key, generation):
    state = vc_member_pending.get(key)
    if not state or state.get("generation") != generation:
        return
    try:
        remaining = max(0.0, state["due_at"] - time.monotonic())
        if remaining > 0:
            await asyncio.sleep(remaining)
        state = vc_member_pending.get(key)
        if not state or state.get("generation") != generation:
            return
        member = state["member"]
        channel = state["channel"]
        target_id = state["target_id"]
        if _vc_current_channel_id(member) == target_id:
            vc_member_pending.pop(key, None)
            return
        requested_at = time.monotonic()
        _vc_event(
            state["guild_id"],
            last_member=state["member_name"],
            last_target=state["target_name"],
            last_requested_at=requested_at,
        )
        print(
            f"[Voice {BOT_VERSION}] Delay MOVE {state['member_name']} -> {state['target_name']} "
            f"after {max(0.0, requested_at - state['detected_at']):.3f}s "
            f"(configured {state['delay']:.1f}s)"
        )
        await _vc_original_member_move_to(member, channel, reason=state.get("reason"))
        completed_at = time.monotonic()
        vc_member_recent_target[key] = (target_id, completed_at)
        _vc_event(
            state["guild_id"],
            last_completed_at=completed_at,
            last_member=state["member_name"],
            last_target=state["target_name"],
        )
        current = vc_member_pending.get(key)
        if current and current.get("generation") == generation:
            vc_member_pending.pop(key, None)
        print(
            f"[Voice {BOT_VERSION}] Delay moved {state['member_name']} -> {state['target_name']} "
            f"API={max(0.0, completed_at - requested_at):.3f}s"
        )
    except asyncio.CancelledError:
        return
    except Exception as exc:
        current = vc_member_pending.get(key)
        if current and current.get("generation") == generation:
            vc_member_pending.pop(key, None)
        print(
            f"[Voice {BOT_VERSION}] Delayed member move failed {key}: "
            f"{type(exc).__name__}: {exc}"
        )


_vc_original_request_json = web.Request.json
async def _vc_request_json_with_move_delay(request, *args, **kwargs):
    payload = await _vc_original_request_json(request, *args, **kwargs)
    if isinstance(payload, dict) and payload.get("protocol_version") == 3:
        raw_guild_id = payload.get("guild_id")
        try:
            guild_id = int(str(raw_guild_id).strip())
        except (TypeError, ValueError):
            guild_id = None
        _vc_request_guild_context.set(guild_id)
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
                print(f"[Voice {BOT_VERSION}] Guild {guild_id} desired-state move delay = {delay:.1f}s")
    return payload
web.Request.json = _vc_request_json_with_move_delay


_vc_original_member_move_to = discord.Member.move_to
async def _vc_desired_state_member_move_to(member, channel, *, reason=None):
    guild = getattr(member, "guild", None)
    guild_id = getattr(guild, "id", None)
    member_id = getattr(member, "id", None)
    if guild_id is None or member_id is None:
        return await _vc_original_member_move_to(member, channel, reason=reason)

    key = (guild_id, member_id)
    target_id = _vc_channel_id(channel)
    target_name = getattr(channel, "name", "Disconnected") if channel is not None else "Disconnected"
    member_name = getattr(member, "display_name", None) or getattr(member, "name", str(member_id))

    # Desired state already matches reality: clear stale pending work.
    if _vc_current_channel_id(member) == target_id:
        _vc_cancel_pending(key, reason=None)
        return None

    # Avoid a duplicate REST move while Discord voice-state propagation catches
    # up immediately after a just-completed request to this same target.
    recent = vc_member_recent_target.get(key)
    now = time.monotonic()
    if recent and recent[0] == target_id and (now - recent[1]) < 2.0:
        return None

    delay = vc_move_delay_by_guild.get(guild_id, VC_DEFAULT_MOVE_DELAY)
    state = vc_member_pending.get(key)

    # Same desired target across repeated Minecraft snapshots MUST NOT restart
    # the timer. If the admin changes delay while pending, preserve detected_at
    # and only recalculate due_at against the new configured delay.
    if state and state.get("target_id") == target_id:
        if abs(state.get("delay", delay) - delay) <= 1e-9:
            return None
        detected_at = state["detected_at"]
        _vc_cancel_pending(key, reason="delay-changed")
    else:
        detected_at = now
        if state:
            _vc_cancel_pending(key, reason="target-changed")
        print(
            f"[Voice {BOT_VERSION}] Delay desired {member_name} -> {target_name}; "
            f"configured={delay:.1f}s"
        )
        _vc_event(
            guild_id,
            last_detected_at=detected_at,
            last_member=member_name,
            last_target=target_name,
        )

    generation = vc_member_generation.get(key, 0) + 1
    vc_member_generation[key] = generation
    due_at = detected_at + delay

    # Delay 0 means immediate at the first allocator decision; only snapshot,
    # HTTP and Discord API latency remain.
    if due_at <= now + 1e-6:
        requested_at = time.monotonic()
        _vc_event(
            guild_id,
            last_requested_at=requested_at,
            last_member=member_name,
            last_target=target_name,
        )
        print(
            f"[Voice {BOT_VERSION}] Delay MOVE {member_name} -> {target_name} "
            f"after {max(0.0, requested_at - detected_at):.3f}s (configured {delay:.1f}s)"
        )
        result = await _vc_original_member_move_to(member, channel, reason=reason)
        completed_at = time.monotonic()
        vc_member_recent_target[key] = (target_id, completed_at)
        _vc_event(guild_id, last_completed_at=completed_at)
        print(
            f"[Voice {BOT_VERSION}] Delay moved {member_name} -> {target_name} "
            f"API={max(0.0, completed_at - requested_at):.3f}s"
        )
        return result

    pending = {
        "guild_id": guild_id,
        "member": member,
        "member_name": member_name,
        "channel": channel,
        "target_id": target_id,
        "target_name": target_name,
        "detected_at": detected_at,
        "due_at": due_at,
        "delay": delay,
        "reason": reason,
        "generation": generation,
        "task": None,
    }
    vc_member_pending[key] = pending
    pending["task"] = asyncio.create_task(_vc_execute_pending_move(key, generation))
    print(
        f"[Voice {BOT_VERSION}] Delay scheduled {member_name} -> {target_name} "
        f"in {max(0.0, due_at - now):.3f}s"
    )
    return None

discord.Member.move_to = _vc_desired_state_member_move_to


# Inject applied-delay and pending timer diagnostics into the normal
# /update_coords JSON response when the base V1.7.0 handler uses web.json_response.
_vc_original_json_response = web.json_response
def _vc_json_response_with_move_delay(data=None, *args, **kwargs):
    guild_id = _vc_request_guild_context.get()
    if guild_id is not None and isinstance(data, dict) and "ic_map" in data and "commands" in data:
        now = time.monotonic()
        pending = []
        for (pending_guild_id, _member_id), state in list(vc_member_pending.items()):
            if pending_guild_id != guild_id:
                continue
            task = state.get("task")
            if task is not None and task.done():
                continue
            pending.append(max(0.0, state.get("due_at", now) - now))
        event = vc_move_events_by_guild.get(guild_id, {})
        enriched = dict(data)
        enriched["move_delay_applied"] = vc_move_delay_by_guild.get(guild_id, VC_DEFAULT_MOVE_DELAY)
        enriched["move_delay_debug"] = {
            "pending_count": len(pending),
            "min_remaining": round(min(pending), 3) if pending else 0.0,
            "max_remaining": round(max(pending), 3) if pending else 0.0,
            "last_member": event.get("last_member"),
            "last_target": event.get("last_target"),
            "last_detected_age": round(max(0.0, now - event["last_detected_at"]), 3) if event.get("last_detected_at") else None,
            "last_requested_age": round(max(0.0, now - event["last_requested_at"]), 3) if event.get("last_requested_at") else None,
            "last_completed_age": round(max(0.0, now - event["last_completed_at"]), 3) if event.get("last_completed_at") else None,
        }
        data = enriched
    return _vc_original_json_response(data, *args, **kwargs)
web.json_response = _vc_json_response_with_move_delay


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


# --- ระบบจัดการห้องเสียง V1.7.5: Acoustic Groups only ---''', "voice helper + desired-state delay")

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

exec(compile(_source, "bot_v1.7.5.py", "exec"), globals(), globals())
