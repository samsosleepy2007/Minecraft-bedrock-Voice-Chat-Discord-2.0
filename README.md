# Minecraft Bedrock Voice Chat Discord 2.0 — Bot V1.7.4 / Addon V1.7.4

Discord Bot + Minecraft Bedrock Voice Chat Connector สำหรับระบบ Proximity Voice แบบ Acoustic Groups / Raycast

## อัปเดตล่าสุด — V1.7.4 Acoustic Barrier + Move Delay + Realtime Performance

V1.7.4 ต่อจาก symmetric Raycast ของ V1.7.3 โดยเพิ่มการวิเคราะห์ขนาดสิ่งกีดขวางให้สมจริงขึ้น, เพิ่มค่าหน่วงการย้าย Discord Voice ที่ตั้งจาก Addon ได้ และเพิ่ม Performance Counter แบบ realtime ใน Action Bar ของผู้เล่นทุกคนระหว่าง `/test`.

## Addon V1.7.4 — Range-scaled Acoustic Barrier

V1.7.3 ใช้หลักว่า Direct Ray ถูก block แล้วเส้นเสียงระดับนั้นถูก block ทันที ซึ่งทำให้เสาหรือกำแพงเตี้ยขนาดเล็กสามารถตัดเสียงได้แรงเกินจริง

V1.7.4 เพิ่ม `Barrier Span Analyzer` หลัง Direct Ray ชนสิ่งกีดขวาง:

```text
Direct symmetric ray
        ↓
      blocked?
   ├─ no  → clear
   └─ yes
        ↓
วัด effective wall width
        ↓
วัด effective wall height
        ↓
width >= ceil(Range)
AND
height >= ceil(Range)
        ↓
Acoustic barrier
```

ตัวอย่างเมื่อ Mic Range = `5` blocks:

| Barrier | ผล |
| --- | --- |
| 1 × 2 | เสียงผ่าน |
| 4 × 5 | เสียงผ่าน |
| 5 × 4 | เสียงผ่าน |
| 5 × 5 | กันเสียง |
| 6 × 5 | กันเสียง |

กฎสำคัญ:

- ใช้ `ceil(Mic Range)` เป็น threshold ของ barrier
- ต้องผ่านทั้งเงื่อนไขความกว้างและความสูงจึงกันเสียง
- ใช้ Range ปกติ `R` เป็นขนาด barrier ไม่ใช้ Leave Range `R + 2`
- ยังรักษา Head OR Chest acoustic path
- ยังรักษา symmetric A→B และ B→A จาก V1.7.3
- ไม่ hardcode วัสดุหรือ Door โดยเฉพาะ
- Direct Ray ผ่านช่องประตูที่เปิดอยู่ → เชื่อมเสียงได้ทันที
- ประตูปิดที่เป็นส่วนหนึ่งของกำแพงขนาดใหญ่พอ → ตัดเสียง
- สิ่งกีดขวางเล็ก เช่นเสาหรือกำแพงเตี้ย สามารถให้เสียงอ้อม/ข้ามได้

### Performance optimization ของ Barrier Analyzer

เพื่อไม่ให้ BDS scan block เป็น cube ทุกคู่ ระบบใช้:

- scan เฉพาะแนวกว้าง + แนวสูงแบบประมาณ `O(R)`
- early exit ถ้าความกว้างไม่ถึง threshold
- per-snapshot `pairCache`
- per-snapshot `Barrier Cache`
- Direct Ray clear จะไม่เข้า Barrier Analyzer

ดังนั้น open field มี overhead เพิ่มจาก V1.7.3 น้อยมาก และพื้นที่อาคารจะได้ประโยชน์จาก cache เมื่อหลายคู่ชน barrier บริเวณเดียวกัน

## Realtime `/test` Performance Counter

เมื่อ Discord `/test` ทำงานและ Addon พบ `botvc` จะเปิด detailed profiler อัตโนมัติ และแสดงผล realtime ใน Minecraft Action Bar ของ **ผู้เล่นทุกคน**.

ตัวอย่าง:

```text
VC TEST PERF 3ms (avg 2.4 / max 5) | Tick 6.0% | P8 G3 Pair18 Ray31 Wall6 Cache4
```

ค่าที่เก็บระหว่าง Test ได้แก่:

- `last_ms` — เวลาของ Acoustic cycle ล่าสุด
- `avg_ms` — ค่าเฉลี่ยจาก sample ล่าสุดสูงสุด 20 รอบ
- `max_ms` — peak ของ sample window
- `tick_budget_pct` — เวลา Acoustic เทียบกับ tick budget 50ms
- จำนวน Players / Entities / Groups
- Candidate pairs / unique pair checks
- pair cache hits
- Raycast count / blocked rays
- Barrier scans / Barrier cache hits
- Block checks

Performance Action Bar มี priority เหนือ Action Bar สถานะ Mic/Headphone เดิมเฉพาะตอน `/test` active. เมื่อ Test จบ ระบบจะปิด detailed profiling, reset sample และคืน Action Bar ปกติของแต่ละผู้เล่นอัตโนมัติ

Detailed profiling ไม่เปิดตลอดเวลา จึงลด overhead ในการใช้งาน production ปกติ

## Voice Move Delay Setting

หน้า Setup ของ Addon V1.7.4 เพิ่ม:

```text
Voice Move Delay: 0.0 – 5.0 seconds
step: 0.1
recommended/default: 3.0
```

ถ้าเลือกค่าต่ำกว่า `3.0` วินาที Addon จะยังไม่บันทึกทันที แต่แสดงคำเตือนว่าการย้ายสมาชิกถี่อาจเพิ่มโอกาสชน Discord API rate limit หรือทำให้ Voice routing ไม่เสถียร แล้วให้เลือก:

- ยืนยันใช้ค่าที่เลือก
- คืนค่าหน่วงเดิม

ค่าถูกเก็บใน Dynamic Property:

```text
vc:move_delay
```

ถ้าค่าไม่มีหรือ invalid จะ fallback เป็น `3.0` วินาที

## Discord Bot V1.7.4

Bot V1.7.4 รับ `move_delay` จาก Addon ผ่าน Protocol V3 optional field และใช้กับการย้ายสมาชิก Discord Voice จริง

การเปลี่ยนแปลง:

- clamp `move_delay` เป็น `0.0–5.0`
- invalid / missing → `3.0`
- แยก setting ต่อ Discord Guild
- throttle แยกต่อ Discord Member
- ไม่ใช้ `sleep` ต่อผู้เล่นแบบ serial queue
- ถ้าสมาชิกอยู่ target Voice Channel อยู่แล้ว จะไม่ยิง move request ซ้ำ
- ปิด legacy global `MOVE_COOLDOWN = 3.0` gate แล้วให้ V1.7.4 wrapper เป็นผู้จัดการ throttling
- รักษา `ensure_bot_voice_connection()` ของ V1.7.3 สำหรับ Discord Bot VoiceClient
- รักษา `/test` fallback และ Acoustic routing เดิม

ตัวอย่างเชิงพฤติกรรม:

```text
A เพิ่งถูกย้าย → A รอ cooldown ของ A
B ยังไม่เคยถูกย้าย → B ยังย้ายได้ทันที
```

จึงไม่ทำให้ cooldown ของสมาชิกหนึ่งคนบล็อกการย้ายของสมาชิกคนอื่นทั้ง Guild

## Protocol V3 — Optional Extensions

Protocol version ยังคงเป็น:

```text
protocol_version = 3
```

Addon V1.7.4 เพิ่ม optional fields:

```json
{
  "move_delay": 3.0,
  "acoustic_perf": {
    "last_ms": 3,
    "avg_ms": 2.4,
    "max_ms": 5,
    "tick_budget_pct": 6.0,
    "players": 8,
    "groups": 3,
    "unique_pairs": 18,
    "raycasts": 31,
    "barrier_scans": 6,
    "barrier_cache_hits": 4,
    "block_checks": 47
  }
}
```

`acoustic_perf` ถูกส่งเฉพาะเมื่อ `/test` active / `botvc` อยู่ใน snapshot. `move_delay` ส่งทุก snapshot เพื่อให้ Bot ใช้ runtime setting ล่าสุด

## Regression ที่ตรวจสำหรับ V1.7.4

Barrier behavior:

```text
Range 5 + 1x2 obstacle  -> connect
Range 5 + 4x5 wall      -> connect
Range 5 + 5x4 wall      -> connect
Range 5 + 5x5 wall      -> blocked
Range 5 + 6x5 wall      -> blocked
Open doorway             -> connect
```

Group transition โดยไม่ขยับตำแหน่ง:

```text
open               -> [A,B]
close 5x5 barrier  -> [A] [B]
open               -> [A,B]
small 1x2 obstacle -> [A,B]
```

ตรวจเพิ่มเติม:

- JavaScript syntax: ผ่าน
- JSON manifests: ผ่าน
- ZIP CRC / integrity: ผ่าน
- pack entries: 81
- Behavior Pack / Resource Pack version: `[1,7,4]`
- UUID เดิมยังคงเดิม
- Bot V1.7.4 Python compile/static validation: ผ่าน

> การทดสอบเหล่านี้เป็น static/mock validation. ยังควรทดสอบ geometry, BDS performance และ Discord Voice/rate-limit behavior บน production server จริง

## Addon V1.7.4 Package

SHA-256 ของ package ที่ build/test:

```text
7595c83d603a758a66c379c3447182436922ed0caf51088e5d38f5e8d4cd57a0
```

Source patch ใน repository:

```text
addon-patches/v1.7.4-acoustic-barrier-perf-delay.patch
```

## V1.7.3 — Symmetric Occlusion Fix ที่ยังคงอยู่

V1.7.3 แก้กรณี existing group ไม่แตกเมื่อปิดประตูเพราะ Raycast direction สามารถต่างกันระหว่าง preserve และ rejoin:

```text
Preserve: B → A
Rejoin:   A → B
```

แก้โดย:

- Head A→B + B→A
- Chest A→B + B→A
- ลด endpoint trim จาก `0.25` เป็น epsilon `0.02`
- Raycast result ไม่ขึ้นกับทิศทางของ pair

V1.7.4 รักษา behavior นี้ทั้งหมดก่อนนำ Barrier Span Analyzer มาตัดสิน final occlusion

## V1.7.2 — Re-entry Acoustic Fix ที่ยังคงอยู่

V1.7.2 เพิ่ม reconciliation/merge pass หลังกลุ่มแตก เพื่อให้:

```text
[A,B]
  ↓ ออกเกิน R+2
[A] [B]
  ↓ กลับเข้า R + acoustic path ผ่าน
[A,B]
```

ยังคง:

- Join Range = `R`
- Leave Range = `R + 2`
- Dimension separation
- Centroid constraint
- Strict pair distance
- no chain clustering

## Test Voice System

- `/test` ใช้ registered Xbox Gamertag
- Bot ส่ง `spawn_test_bot` ผ่าน `/update_coords`
- Addon เสก Armor Stand `botvc` พร้อม tag `vc:test_bot`
- `botvc` เข้า Acoustic Group เหมือน participant จริง
- Discord Bot VoiceClient connect/move ตาม Acoustic Group ของ `botvc`
- `/test` ซ้ำโดย owner ปิด Test, disconnect Bot และลบ `botvc`
- command ID + `command_acks` ป้องกัน command ซ้ำ
- stale `botvc` cleanup หลัง Bot restart

## Legacy Zone / Room

V1.7.x ไม่ใช้ Zone / Part / Room เป็น dependency ของ proximity:

- ไม่มี HTTP `/zones` และ `/zone/*`
- ไม่มี Discord `/zone`, `/zones`, `/delzone`, `/zonerange`, `/range`
- ไม่มี Zone/Room routing หรือ legacy centroid fallback
- Minecraft Acoustic Groups เป็น source of truth ของ proximity

## Commands

- `/setup` — ตั้ง Main Voice Category + Lobby
- `/backup` — สำรองข้อมูล Bot
- `/restore` — กู้ข้อมูล Bot
- `/whitelist` — จัดการ whitelist
- `/test` — Test `botvc` + เปิด realtime Acoustic Performance Counter ในเกม

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

> runtime Bot V1.7.4 ใช้ hotfix layer ใน `bot.py` ครอบ source V1.7.0 ที่เก็บแบบ XZ+Base64 เพื่อรักษา source baseline เดิมของ repository
