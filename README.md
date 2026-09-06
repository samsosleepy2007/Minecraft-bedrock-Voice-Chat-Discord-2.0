# Minecraft Bedrock Voice Chat Discord 2.0 — Bot V1.7.5 / Addon V1.7.5

Discord Bot + Minecraft Bedrock Voice Chat Connector สำหรับระบบ Proximity Voice แบบ Acoustic Groups / Raycast

## V1.7.5 — Acoustic Span Accuracy + Desired-State Move Delay

V1.7.5 แก้สองประเด็นจาก V1.7.4:

1. Barrier Span เดิมนับ cell แบบ `non-air = wall` ทำให้ geometry บางชนิดมีโอกาสถูกนับเป็นความกว้าง/สูงของกำแพงทั้งที่ acoustic ray ควรผ่านได้
2. `Voice Move Delay` เดิมเป็น cooldown หลังการย้ายครั้งก่อน ไม่ใช่เวลาหน่วงหลัง desired Voice Channel เปลี่ยนจริง จึงทำให้ค่าที่ตั้ง `0` หรือ `5` ไม่สัมพันธ์กับเวลาที่ผู้ใช้ถูกย้ายอย่างที่คาด

## Addon V1.7.5 — Acoustic-blocking Barrier Span

กติกาหลักยังคงเดิม:

```text
Barrier blocks voice เมื่อ:
width >= ceil(Mic Range)
AND
height >= ceil(Mic Range)
```

ตัวอย่าง Range = `5`:

| Barrier | ผล |
| --- | --- |
| 1 × 2 | เชื่อม |
| 4 × 5 | เชื่อม |
| 5 × 3 | เชื่อม |
| 5 × 4 | เชื่อม |
| 5 × 5 | กันเสียง |
| 6 × 5 | กันเสียง |

V1.7.5 เปลี่ยนตัวตรวจ span cell จากการเช็กว่า block ไม่ใช่ air/liquid อย่างเดียว เป็น short collision-aware ray probes ที่ใช้ `getBlockFromRay(... includePassableBlocks:false)` ในทิศของ acoustic path แล้ว cache ผลต่อ snapshot

ผลคือ passable/open geometry จะไม่ถูกนับเพิ่มเข้า width/height แบบง่าย ๆ ขณะที่ closed/full geometry ยังสามารถเป็นส่วนหนึ่งของ Acoustic Barrier ได้

ยังคงระบบเดิมทั้งหมด:

- symmetric A→B / B→A raycast จาก V1.7.3
- Head OR Chest path
- Join Range = `R`
- Leave Range = `R + 2`
- Dimension separation
- Centroid constraint
- Strict pair validation
- stable merge / re-entry fix จาก V1.7.2
- per-snapshot pair cache
- Barrier Span scan ประมาณ `O(R)` ไม่ scan cube

## Bot V1.7.5 — Desired-State Debounce Timer

`move_delay` มีความหมายใหม่ที่ตรงกับ UI:

> เมื่อ Bot ตรวจพบว่า desired Discord Voice Channel ของสมาชิกเปลี่ยน ต้องให้ target ใหม่นั้นคงที่ครบ `move_delay` วินาทีก่อนจึงย้าย

ตัวอย่าง `move_delay = 5.0`:

```text
t=0.0  desired Room1 -> Room2
       start timer

t=1.0  snapshot ยังต้อง Room2
       timer เดิมเดินต่อ ไม่ reset

t=5.0  target ยังเป็น Room2
       MOVE
```

ถ้า target เปลี่ยนก่อนครบเวลา:

```text
t=0.0  target Room2

t=2.0  target กลับ Room1
       cancel pending Room2
       ไม่เกิด stale move
```

กฎสำคัญ:

- `0.0` → move ใน allocator decision แรก เหลือเพียง Minecraft snapshot / network / Discord API latency
- `0.1–5.0` → target ต้องนิ่งครบเวลาที่ตั้ง
- snapshot ซ้ำ target เดิมไม่ reset timer
- เปลี่ยน target → cancel pending เก่าและเริ่ม desired state ใหม่
- แยก pending timer ต่อ Discord Member
- legacy `MOVE_COOLDOWN = 3.0` ถูกปิดเพื่อไม่ให้มี second 3-second gate
- ไม่ส่ง move ซ้ำถ้า Discord state ตรง target แล้ว
- มี short duplicate suppression หลัง move สำเร็จเพื่อรอ Voice State propagation

## `/test` Realtime Diagnostics

Performance Counter ใน Minecraft Action Bar ยังทำงานแบบ realtime สำหรับผู้เล่นทุกคนเมื่อ `/test` active และมี `botvc`

V1.7.5 เพิ่มข้อมูล Move Delay:

```text
VC TEST PERF 3ms (avg 2.4 / max 5)
| Tick 6.0% | P8 G3 Pair18 Ray31 Wall6 Cache4
| Dcfg5.0 Bot5.0 Pend1:2.7s
```

ความหมาย:

- `Dcfg` — ค่าที่ Addon ตั้งและส่งไป
- `Bot` — ค่าที่ Bot parse/apply แล้ว
- `Pend` — จำนวน pending member moves และ remaining ต่ำสุด

Bot เพิ่ม optional response fields:

```json
{
  "move_delay_applied": 5.0,
  "move_delay_debug": {
    "pending_count": 1,
    "min_remaining": 2.7,
    "max_remaining": 2.7,
    "last_member": "PlayerA",
    "last_target": "Voice Room 2",
    "last_detected_age": 2.3,
    "last_requested_age": null,
    "last_completed_age": null
  }
}
```

Render logs จะมี timestamp แบบ monotonic สำหรับ desired target, scheduled timer, move request และ completion เพื่อแยกว่า latency เกิดที่ timer หรือ Discord API

## Voice Move Delay Setting

Addon UI:

```text
0.0 – 5.0 seconds
step = 0.1
default/recommended = 3.0
```

ค่าต่ำกว่า `3.0` ยังคงมีหน้าคำเตือนและให้เลือกยืนยันหรือคืนค่าเดิม

Dynamic Property:

```text
vc:move_delay
```

Protocol V3 optional field:

```json
{
  "move_delay": 3.0
}
```

ค่า invalid / missing ฝั่ง Bot fallback เป็น `3.0`

## Regression V1.7.5

Barrier mock regression:

```text
1x2  -> connect
4x5  -> connect
5x3  -> connect
5x4  -> connect
5x5  -> blocked
6x5  -> blocked
```

Desired-state delay regression:

```text
0.0     -> immediate decision path
repeated same target -> timer does not reset
pending target       -> no move before due time
target changes       -> old pending move cancelled
5.0     -> due_at = detected_at + 5.0 exactly
```

Package/static validation:

- JavaScript `node --check`: ผ่าน
- Bot Python compile: ผ่าน
- JSON parse: 18 files ผ่าน
- ZIP CRC/integrity: ผ่าน
- package entries: 81
- BP/RP version: `[1,7,5]`
- UUID เดิมยังคงเดิม

> Barrier และ delay tests ข้างต้นเป็น static/mock regression. BDS geometry จริงและ Discord Voice latency/rate-limit ควรยืนยันบน server จริงด้วย `/test` diagnostics ใหม่

## Addon V1.7.5 Package

SHA-256:

```text
d5c02b3b1732a4e4188b745108c15da6284bb51312854064a69e0f4b7adf7852
```

Source patch:

```text
addon-patches/v1.7.5-acoustic-span-desired-delay.patch
```

## Version History ที่ยังคงอยู่

### V1.7.4

- Range-scaled Barrier Span
- Voice Move Delay UI `0–5`
- realtime `/test` Performance Counter

### V1.7.3

- symmetric Head/Chest raycast A→B + B→A
- endpoint epsilon `0.02`
- ปิดประตูสามารถตัด existing group ได้ทันที

### V1.7.2

- acoustic group re-entry reconciliation / merge pass
- Join `R`, Leave `R+2`
- strict pair + centroid + no chain clustering

## Test Voice System

- `/test` ใช้ registered Xbox Gamertag
- Bot ส่ง `spawn_test_bot` ผ่าน `/update_coords`
- Addon เสก Armor Stand `botvc` พร้อม tag `vc:test_bot`
- `botvc` เข้า Acoustic Group เหมือน participant จริง
- Discord Bot VoiceClient connect/move ตาม Acoustic Group ของ `botvc`
- `/test` ซ้ำโดย owner ปิด Test, disconnect Bot และลบ `botvc`
- command ID + `command_acks` ป้องกัน command ซ้ำ
- stale `botvc` cleanup หลัง Bot restart

## Architecture

Minecraft Acoustic Groups เป็น source of truth ของ proximity. Discord Bot นำ desired groups ไปจัด Voice Channel โดย Phone Call / Group Call มี priority เหนือ proximity ตามระบบเดิม

Legacy Zone / Part / Room ไม่ใช่ dependency ของ proximity ใน V1.7.x

## Commands

- `/setup` — ตั้ง Main Voice Category + Lobby
- `/backup` — สำรองข้อมูล Bot
- `/restore` — กู้ข้อมูล Bot
- `/whitelist` — จัดการ whitelist
- `/test` — Test `botvc` + realtime performance / delay diagnostics

## Run Bot

```bash
pip install -r requirements.txt
python bot.py
```

Environment variables:

- `DISCORD_TOKEN`
- `DASHBOARD_PASS`
- `PORT`
- `LOG_WEBHOOK_URL` (optional)

Bot runtime ใช้ hotfix layer ใน `bot.py` ครอบ lossless V1.7.0 source ที่เก็บใน `bot_source.py.xz.b64`.
